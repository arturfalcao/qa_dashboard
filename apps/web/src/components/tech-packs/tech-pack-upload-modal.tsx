'use client'

import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Upload, FileText, X, Sparkles, CheckCircle2 } from 'lucide-react'

interface TechPackUploadModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function TechPackUploadModal({ isOpen, onClose, onSuccess }: TechPackUploadModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [styleRef, setStyleRef] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const queryClient = useQueryClient()

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No file selected')
      return apiClient.uploadTechPackFile(file, styleRef || undefined)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tech-packs'] })
      resetForm()
      onSuccess()
    },
  })

  const resetForm = () => {
    setFile(null)
    setStyleRef('')
  }

  const handleClose = () => {
    resetForm()
    onClose()
  }

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (isValidFile(droppedFile)) {
        setFile(droppedFile)
      }
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      if (isValidFile(selectedFile)) {
        setFile(selectedFile)
      }
    }
  }

  const isValidFile = (file: File) => {
    const validTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
    ]
    const validExtensions = ['.pdf', '.xlsx', '.xls']
    const extension = '.' + file.name.split('.').pop()?.toLowerCase()

    return validTypes.includes(file.type) || validExtensions.includes(extension)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-gradient-to-r from-violet-500 to-purple-500">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            Upload Tech Pack
          </DialogTitle>
          <DialogDescription>
            Upload a PDF or Excel file to automatically extract product specifications using AI.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Style Ref Input */}
          <div>
            <label htmlFor="styleRef" className="block text-sm font-medium text-slate-700 mb-1">
              Style Reference (optional)
            </label>
            <input
              id="styleRef"
              type="text"
              value={styleRef}
              onChange={(e) => setStyleRef(e.target.value)}
              placeholder="e.g., SS24-SHIRT-001"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-slate-500">
              If not provided, it will be extracted from the document.
            </p>
          </div>

          {/* File Upload Area */}
          <div
            className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragActive
                ? 'border-violet-500 bg-violet-50'
                : file
                ? 'border-green-300 bg-green-50'
                : 'border-slate-200 hover:border-violet-300 hover:bg-slate-50'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {file ? (
              <div className="space-y-3">
                <div className="flex items-center justify-center">
                  <div className="p-3 rounded-full bg-green-100">
                    <CheckCircle2 className="h-8 w-8 text-green-600" />
                  </div>
                </div>
                <div>
                  <p className="font-medium text-slate-900">{file.name}</p>
                  <p className="text-sm text-slate-500">{formatFileSize(file.size)}</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setFile(null)}
                  className="text-slate-500 hover:text-slate-700"
                >
                  <X className="h-4 w-4 mr-1" />
                  Remove
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-center">
                  <div className="p-3 rounded-full bg-violet-100">
                    <Upload className="h-8 w-8 text-violet-600" />
                  </div>
                </div>
                <div>
                  <p className="font-medium text-slate-900">
                    Drop your tech pack here, or{' '}
                    <label className="text-violet-600 hover:text-violet-700 cursor-pointer underline">
                      browse
                      <input
                        type="file"
                        className="hidden"
                        accept=".pdf,.xlsx,.xls"
                        onChange={handleFileChange}
                      />
                    </label>
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    Supports PDF and Excel files (max 50MB)
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Info Box */}
          <div className="bg-gradient-to-r from-violet-50 to-purple-50 border border-violet-100 rounded-lg p-4">
            <div className="flex gap-3">
              <FileText className="h-5 w-5 text-violet-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-violet-900">AI-Powered Extraction</p>
                <p className="text-violet-700 mt-1">
                  Our AI will automatically extract style reference, product name, measurements,
                  colorways, materials, care instructions, and more from your tech pack.
                </p>
              </div>
            </div>
          </div>

          {/* Error Message */}
          {uploadMutation.isError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              {uploadMutation.error instanceof Error
                ? uploadMutation.error.message
                : 'Failed to upload tech pack. Please try again.'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={() => uploadMutation.mutate()}
            disabled={!file}
            loading={uploadMutation.isPending}
            className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700"
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload & Extract
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
