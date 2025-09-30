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
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectOption } from '@/components/ui/select'
import { EmptyState } from '@/components/ui/empty-state'
import { useToast } from '@/components/ui/toast'

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
  [ReportStatus.PENDING]: { label: 'Pending', icon: ClockIcon, color: 'text-warning-600' },
  [ReportStatus.GENERATING]: { label: 'Generating', icon: ClockIcon, color: 'text-primary-600' },
  [ReportStatus.READY]: { label: 'Ready', icon: CheckCircleIcon, color: 'text-success-600' },
  [ReportStatus.COMPLETED]: { label: 'Completed', icon: CheckCircleIcon, color: 'text-success-600' },
  [ReportStatus.FAILED]: { label: 'Failed', icon: XCircleIcon, color: 'text-danger-600' },
  [ReportStatus.EXPIRED]: { label: 'Expired', icon: AlertCircleIcon, color: 'text-neutral-500' },
}

export default function ReportsPage() {
  const [selectedType, setSelectedType] = useState<string>('')
  const [showGenerateModal, setShowGenerateModal] = useState(false)
  const queryClient = useQueryClient()
  const { publish } = useToast()

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ['reports', selectedType],
    queryFn: () => apiClient.getReports(selectedType || undefined),
  })

  const downloadMutation = useMutation({
    mutationFn: async (reportId: string) => {
      const blob = await apiClient.downloadReport(reportId)
      const report = reports.find((r) => r.id === reportId)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = report?.fileName || `report-${reportId}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    },
    onSuccess: () => {
      publish({ variant: 'success', title: 'Download started' })
    },
    onError: (error: any) => {
      publish({ variant: 'danger', title: 'Download failed', description: error?.message })
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

    Object.keys(grouped).forEach((type) => {
      grouped[type].sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
      )
    })

    return grouped
  }, [reports])

  const handleDownload = (reportId: string) => {
    downloadMutation.mutate(reportId)
  }

  const handleGenerateComplete = () => {
    queryClient.invalidateQueries({ queryKey: ['reports'] })
    setShowGenerateModal(false)
    publish({ variant: 'success', title: 'Report generation started' })
  }

  const filterOptions = useMemo<SelectOption<string>[]>(
    () => [
      { value: '', label: 'All report types' },
      ...Object.entries(REPORT_TYPE_LABELS).map(([type, label]) => ({ value: type, label })),
    ],
    [],
  )

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Reports"
          description="Generate, view, and download quality assurance reports."
          actions={
            <Button onClick={() => setShowGenerateModal(true)}>
              <PlusIcon className="mr-2 h-4 w-4" /> Generate report
            </Button>
          }
        />
        <Card>
          <CardContent className="flex h-48 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Reports"
        description="Generate, view, and download quality assurance reports."
        actions={
          <Button onClick={() => setShowGenerateModal(true)}>
            <PlusIcon className="mr-2 h-4 w-4" /> Generate report
          </Button>
        }
      />

      <Card>
        <CardContent className="flex flex-col gap-4 p-6">
          <div className="flex items-center gap-3 text-sm text-neutral-600">
            <FilterIcon className="h-4 w-4 text-neutral-400" />
            <span>Filter by type</span>
          </div>
          <Select value={selectedType} onChange={(value) => setSelectedType(value as string)} options={filterOptions} />
        </CardContent>
      </Card>

      {Object.keys(groupedReports).length === 0 ? (
        <EmptyState
          icon={<FileTextIcon className="h-5 w-5" />}
          title="No reports yet"
          description={selectedType ? 'No reports of this type have been generated yet.' : 'Generate a report to share insights with stakeholders.'}
          action={{ label: 'Generate report', onClick: () => setShowGenerateModal(true) }}
        />
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedReports).map(([type, typeReports]) => (
            <Card key={type}>
              <CardHeader className="flex items-center justify-between">
                <div>
                  <CardTitle>{REPORT_TYPE_LABELS[type as ReportType] || type}</CardTitle>
                  <CardDescription>{typeReports.length} report{typeReports.length === 1 ? '' : 's'} generated.</CardDescription>
                </div>
              </CardHeader>
              <CardContent className="divide-y divide-neutral-200">
                {typeReports.map((report: any) => {
                  const statusMeta = REPORT_STATUS_META[report.status as ReportStatus]
                  const StatusIcon = statusMeta.icon
                  const canDownload =
                    report.status === ReportStatus.COMPLETED || report.status === ReportStatus.READY

                  return (
                    <div key={report.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-start gap-3">
                        <StatusIcon className={`mt-1 h-5 w-5 ${statusMeta.color}`} />
                        <div>
                          <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                            {report.fileName}
                          </p>
                          <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-500">
                            <span>Created {formatDate(report.createdAt)}</span>
                            {report.generatedAt && <span>Generated {formatDate(report.generatedAt)}</span>}
                            <span>Status: {statusMeta.label}</span>
                            {report.language && (
                              <span>
                                Language: {report.language === ReportLanguage.EN ? 'English' : report.language}
                              </span>
                            )}
                            {report.fileSize && (
                              <span>{(report.fileSize / 1024).toFixed(1)} KB</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleDownload(report.id)}
                          disabled={!canDownload || downloadMutation.isPending}
                        >
                          <DownloadIcon className="mr-2 h-4 w-4" /> Download
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showGenerateModal && (
        <ReportGenerationModal
          isOpen={showGenerateModal}
          onClose={() => setShowGenerateModal(false)}
          onSuccess={handleGenerateComplete}
        />
      )}
    </div>
  )
}
