'use client'

import { useState } from 'react'
import { XIcon } from 'lucide-react'

interface ApprovalModalProps {
  isOpen: boolean
  onClose: () => void
  onApprove: (comment: string) => void
  isLoading: boolean
  type: 'approve' | 'reject'
}

export function ApprovalModal({ isOpen, onClose, onApprove, isLoading, type }: ApprovalModalProps) {
  const [comment, setComment] = useState('')

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (type === 'reject' && !comment.trim()) {
      return // Reject requires a comment
    }
    
    onApprove(comment.trim())
  }

  const title = type === 'approve' ? 'Approve Batch' : 'Reject Batch'
  const buttonText = type === 'approve' ? 'Approve' : 'Reject'
  const buttonColor = type === 'approve' 
    ? 'bg-green-600 hover:bg-green-700' 
    : 'bg-red-600 hover:bg-red-700'

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full">
        <div className="flex items-center justify-between p-6 border-b">
          <h3 className="text-lg font-medium text-gray-900">{title}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={isLoading}
          >
            <XIcon className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6">
          <div className="mb-4">
            <label htmlFor="comment" className="block text-sm font-medium text-gray-700 mb-2">
              {type === 'reject' ? 'Reason for rejection *' : 'Comment (optional)'}
            </label>
            <textarea
              id="comment"
              rows={4}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              placeholder={type === 'reject' 
                ? 'Please provide a reason for rejecting this batch...' 
                : 'Add any additional comments...'
              }
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              required={type === 'reject'}
            />
          </div>

          <div className="flex space-x-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || (type === 'reject' && !comment.trim())}
              className={`flex-1 px-4 py-2 text-sm font-medium text-white rounded-md transition-colors disabled:opacity-50 ${buttonColor}`}
            >
              {isLoading ? 'Processing...' : buttonText}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}