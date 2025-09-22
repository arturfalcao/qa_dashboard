'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/components/providers/auth-provider'
import { BatchHeader } from '@/components/batches/batch-header'
import { ApprovalModal } from '@/components/batches/approval-modal'
import { useState } from 'react'
import { UserRole } from '@qa-dashboard/shared'

export default function BatchDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showApprovalModal, setShowApprovalModal] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)

  const batchId = params.id as string
  const tenantSlug = params.tenantSlug as string

  const { data: batch, isLoading } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: () => apiClient.getBatch(batchId),
  })

  const approveMutation = useMutation({
    mutationFn: (comment?: string) => apiClient.approveBatch(batchId, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] })
      queryClient.invalidateQueries({ queryKey: ['batches'] })
      setShowApprovalModal(false)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (comment: string) => apiClient.rejectBatch(batchId, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] })
      queryClient.invalidateQueries({ queryKey: ['batches'] })
      setShowRejectModal(false)
    },
  })

  const handleApprove = (comment: string) => {
    approveMutation.mutate(comment || undefined)
  }

  const handleReject = (comment: string) => {
    rejectMutation.mutate(comment)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => router.back()}
            className="text-gray-500 hover:text-gray-700"
          >
            ← Back
          </button>
        </div>
        
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  if (!batch) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Batch not found</h3>
        <button
          onClick={() => router.back()}
          className="text-primary-600 hover:text-primary-700"
        >
          ← Go back
        </button>
      </div>
    )
  }

  const canApprove = user?.role === UserRole.CLIENT_ADMIN && batch.status === 'awaiting_approval'

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <button
          onClick={() => router.back()}
          className="text-gray-500 hover:text-gray-700 font-medium"
        >
          ← Back to Batches
        </button>
      </div>

      <BatchHeader 
        batch={batch}
        canApprove={canApprove}
        onApprove={() => setShowApprovalModal(true)}
        onReject={() => setShowRejectModal(true)}
      />

      {/* Batch Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v6a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-2xl font-semibold text-gray-900">{batch._count?.garments || 0}</p>
              <p className="text-sm text-gray-500">Total Garments</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-2xl font-semibold text-gray-900">{batch._count?.inspections || 0}</p>
              <p className="text-sm text-gray-500">Inspections</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-2xl font-semibold text-gray-900">{batch._count?.defects || 0}</p>
              <p className="text-sm text-gray-500">Defects Found</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11.707 4.707a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-2xl font-semibold text-gray-900">
                {batch._count?.inspections ? ((batch._count.defects / batch._count.inspections) * 100).toFixed(1) : '0.0'}%
              </p>
              <p className="text-sm text-gray-500">Defect Rate</p>
            </div>
          </div>
        </div>
      </div>

      {/* Audit Log */}
      {batch.approvals && batch.approvals.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Approval History</h3>
          </div>
          <div className="p-6">
            {batch.approvals.map((approval: any) => (
              <div key={approval.id} className="flex items-start space-x-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  approval.decision === 'approved' ? 'bg-green-100' : 'bg-red-100'
                }`}>
                  {approval.decision === 'approved' ? (
                    <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
                <div className="flex-1">
                  <div className="text-sm">
                    <span className="font-medium text-gray-900">
                      {approval.user?.email}
                    </span>
                    <span className={`ml-2 px-2 py-1 text-xs font-medium rounded-full ${
                      approval.decision === 'approved' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {approval.decision.toUpperCase()}
                    </span>
                  </div>
                  {approval.comment && (
                    <p className="text-sm text-gray-600 mt-1">{approval.comment}</p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(approval.decidedAt).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Approval Modal */}
      <ApprovalModal
        isOpen={showApprovalModal}
        onClose={() => setShowApprovalModal(false)}
        onApprove={handleApprove}
        isLoading={approveMutation.isPending}
        type="approve"
      />

      {/* Reject Modal */}
      <ApprovalModal
        isOpen={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        onApprove={handleReject}
        isLoading={rejectMutation.isPending}
        type="reject"
      />
    </div>
  )
}