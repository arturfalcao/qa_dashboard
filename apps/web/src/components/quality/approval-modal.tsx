'use client'

import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Lot } from '@qa-dashboard/shared'
import { CheckCircleIcon, XCircleIcon } from 'lucide-react'

interface ApprovalModalProps {
  lot: Lot | null
  action: 'approve' | 'reject' | null
  isOpen: boolean
  onClose: () => void
  onConfirm: (lotId: string, action: 'approve' | 'reject', note: string) => Promise<void>
}

export function ApprovalModal({ lot, action, isOpen, onClose, onConfirm }: ApprovalModalProps) {
  const [note, setNote] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleClose = () => {
    setNote('')
    setError('')
    onClose()
  }

  const handleSubmit = async () => {
    if (!lot || !action) return

    // Validate note for rejection
    if (action === 'reject' && !note.trim()) {
      setError('Note is required when rejecting a lot')
      return
    }

    setIsSubmitting(true)
    setError('')

    try {
      await onConfirm(lot.id, action, note)
      handleClose()
    } catch (err: any) {
      setError(err.message || 'Failed to process action')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!lot || !action) return null

  const isApprove = action === 'approve'

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {isApprove ? (
              <>
                <CheckCircleIcon className="h-5 w-5 text-green-600" />
                Approve Lot
              </>
            ) : (
              <>
                <XCircleIcon className="h-5 w-5 text-red-600" />
                Reject Lot
              </>
            )}
          </DialogTitle>
          <DialogDescription>
            {isApprove
              ? `You are about to approve lot ${lot.styleRef}. This action will mark it as ready for shipment.`
              : `You are about to reject lot ${lot.styleRef}. Please provide a reason for rejection.`}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <p className="text-slate-500">Style Ref</p>
                  <p className="font-medium text-slate-900">{lot.styleRef}</p>
                </div>
                <div>
                  <p className="text-slate-500">Defect Rate</p>
                  <p className="font-medium text-slate-900">{((lot.defectRate ?? 0) * 100).toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-slate-500">Factory</p>
                  <p className="font-medium text-slate-900">{lot.factory?.name || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-slate-500">Quantity</p>
                  <p className="font-medium text-slate-900">{lot.quantityTotal}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="note" className="text-sm font-medium text-slate-900">
              {isApprove ? 'Note (Optional)' : 'Rejection Reason *'}
            </label>
            <Textarea
              id="note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder={isApprove ? 'Add any comments...' : 'Explain why this lot is being rejected...'}
              rows={4}
              className={error ? 'border-red-300' : ''}
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className={isApprove ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}
          >
            {isSubmitting ? 'Processing...' : isApprove ? 'Approve Lot' : 'Reject Lot'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
