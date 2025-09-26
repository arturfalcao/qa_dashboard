'use client'

import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import {
  FileTextIcon,
  DownloadIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  AlertCircleIcon,
  PlusIcon,
  FilterIcon,
} from 'lucide-react'
import { ReportType, ReportStatus, ReportLanguage } from '@qa-dashboard/shared'
import { ReportGenerationModal } from '@/components/reports/report-generation-modal'

const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  [ReportType.EXECUTIVE_QUALITY_SUMMARY]: 'Executive Quality Summary',
  [ReportType.LOT_INSPECTION_REPORT]: 'Lot Inspection Report',
  [ReportType.MEASUREMENT_COMPLIANCE_SHEET]: 'Measurement Compliance Sheet',
  [ReportType.PACKAGING_READINESS_REPORT]: 'Packaging & Readiness Report',
  [ReportType.SUPPLIER_PERFORMANCE_SNAPSHOT]: 'Supplier Performance Snapshot',
  [ReportType.CAPA_REPORT]: 'CAPA Report',
  [ReportType.INLINE_QC_CHECKPOINTS]: 'Inline QC Checkpoints',
  [ReportType.DPP_SUMMARY]: 'DPP Summary',
  [ReportType.MONTHLY_SCORECARD]: 'Monthly Scorecard',
  [ReportType.LOT]: 'Lot Report',
}

const REPORT_STATUS_META: Record<ReportStatus, { label: string; icon: any; color: string }> = {
  [ReportStatus.PENDING]: { label: 'Pending', icon: ClockIcon, color: 'text-yellow-600' },
  [ReportStatus.GENERATING]: { label: 'Generating', icon: ClockIcon, color: 'text-blue-600' },
  [ReportStatus.READY]: { label: 'Ready', icon: CheckCircleIcon, color: 'text-green-600' },
  [ReportStatus.COMPLETED]: { label: 'Completed', icon: CheckCircleIcon, color: 'text-green-600' },
  [ReportStatus.FAILED]: { label: 'Failed', icon: XCircleIcon, color: 'text-red-600' },
  [ReportStatus.EXPIRED]: { label: 'Expired', icon: AlertCircleIcon, color: 'text-gray-600' },
}

export default function ReportsPage() {
  const [selectedType, setSelectedType] = useState<string>('')
  const [showGenerateModal, setShowGenerateModal] = useState(false)
  const queryClient = useQueryClient()

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ['reports', selectedType],
    queryFn: () => apiClient.getReports(selectedType || undefined),
  })

  const downloadMutation = useMutation({
    mutationFn: async (reportId: string) => {
      const blob = await apiClient.downloadReport(reportId)
      const report = reports.find(r => r.id === reportId)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = report?.fileName || `report-${reportId}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    },
    onError: (error) => {
      console.error('Failed to download report:', error)
    },
  })

  const groupedReports = useMemo(() => {
    const grouped = reports.reduce((acc: Record<string, any[]>, report: any) => {
      const type = report.type
      if (!acc[type]) {
        acc[type] = []
      }
      acc[type].push(report)
      return acc
    }, {})

    // Sort reports within each group by creation date (newest first)
    Object.keys(grouped).forEach(type => {
      grouped[type].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    })

    return grouped
  }, [reports])

  const handleDownload = (reportId: string) => {
    downloadMutation.mutate(reportId)
  }

  const handleGenerateComplete = () => {
    queryClient.invalidateQueries({ queryKey: ['reports'] })
    setShowGenerateModal(false)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="text-sm text-gray-500 mt-1">
            Generate, view, and download quality assurance reports
          </p>
        </div>
        <button
          onClick={() => setShowGenerateModal(true)}
          className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md shadow-sm"
        >
          <PlusIcon className="w-4 h-4 mr-2" />
          Generate Report
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex items-center">
            <FilterIcon className="w-4 h-4 text-gray-400 mr-2" />
            <span className="text-sm font-medium text-gray-700">Filter by type:</span>
          </div>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
          >
            <option value="">All Report Types</option>
            {Object.entries(REPORT_TYPE_LABELS).map(([type, label]) => (
              <option key={type} value={type}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Reports List */}
      {Object.keys(groupedReports).length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <FileTextIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No reports found</h3>
          <p className="text-gray-500 mb-4">
            {selectedType ? 'No reports of this type have been generated yet.' : 'No reports have been generated yet.'}
          </p>
          <button
            onClick={() => setShowGenerateModal(true)}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md"
          >
            <PlusIcon className="w-4 h-4 mr-2" />
            Generate Your First Report
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedReports).map(([type, typeReports]) => (
            <div key={type} className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">
                  {REPORT_TYPE_LABELS[type as ReportType] || type}
                </h3>
                <p className="text-sm text-gray-500">
                  {typeReports.length} report{typeReports.length !== 1 ? 's' : ''}
                </p>
              </div>
              <div className="divide-y divide-gray-200">
                {typeReports.map((report: any) => {
                  const statusMeta = REPORT_STATUS_META[report.status as ReportStatus]
                  const StatusIcon = statusMeta.icon
                  const canDownload = report.status === ReportStatus.COMPLETED || report.status === ReportStatus.READY

                  return (
                    <div key={report.id} className="px-6 py-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-3">
                            <div className="flex-shrink-0">
                              <StatusIcon className={`w-5 h-5 ${statusMeta.color}`} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 truncate">
                                {report.fileName}
                              </p>
                              <div className="flex items-center space-x-4 text-xs text-gray-500">
                                <span>Created {formatDate(report.createdAt)}</span>
                                {report.generatedAt && (
                                  <span>Generated {formatDate(report.generatedAt)}</span>
                                )}
                                {report.fileSize && (
                                  <span>{(report.fileSize / 1024).toFixed(1)} KB</span>
                                )}
                                {report.language && report.language !== 'EN' && (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                    {report.language}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            report.status === ReportStatus.COMPLETED || report.status === ReportStatus.READY
                              ? 'bg-green-100 text-green-800'
                              : report.status === ReportStatus.GENERATING
                              ? 'bg-blue-100 text-blue-800'
                              : report.status === ReportStatus.FAILED
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {statusMeta.label}
                          </span>
                          {canDownload && (
                            <button
                              onClick={() => handleDownload(report.id)}
                              disabled={downloadMutation.isPending}
                              className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                            >
                              <DownloadIcon className="w-3 h-3 mr-1" />
                              Download
                            </button>
                          )}
                          {report.status === ReportStatus.FAILED && report.errorMessage && (
                            <div className="text-xs text-red-600 max-w-xs truncate" title={report.errorMessage}>
                              Error: {report.errorMessage}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      <ReportGenerationModal
        isOpen={showGenerateModal}
        onClose={() => setShowGenerateModal(false)}
        onComplete={handleGenerateComplete}
      />
    </div>
  )
}