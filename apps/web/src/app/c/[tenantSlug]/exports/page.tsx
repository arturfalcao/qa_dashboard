'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, useMemo } from 'react'
import { apiClient } from '@/lib/api'
import { DownloadIcon, FileTextIcon, TableIcon } from 'lucide-react'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Select, SelectOption } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { useToast } from '@/components/ui/toast'

export default function ExportsPage() {
  const [pdfRange, setPdfRange] = useState<'last_7d' | 'last_30d'>('last_7d')
  const [csvRange, setCsvRange] = useState<'last_7d' | 'last_30d'>('last_7d')
  const [selectedLot, setSelectedLot] = useState<string>('')
  const { publish } = useToast()

  const { data: lots = [] } = useQuery({
    queryKey: ['lots'],
    queryFn: () => apiClient.getLots(),
  })

  const lotOptions = useMemo<SelectOption<string>[]>(
    () => [
      { value: '', label: 'All lots' },
      ...lots.map((lot: any) => ({ value: lot.id, label: `${lot.styleRef} • ${lot.factory?.name ?? 'Unassigned'}` })),
    ],
    [lots],
  )

  const rangeOptions: SelectOption<'last_7d' | 'last_30d'>[] = [
    { value: 'last_7d', label: 'Last 7 days' },
    { value: 'last_30d', label: 'Last 30 days' },
  ]

  const pdfMutation = useMutation({
    mutationFn: (payload: { lotId?: string; range?: 'last_7d' | 'last_30d' }) => apiClient.generatePDF(payload),
    onSuccess: (data) => {
      window.open(data.downloadUrl, '_blank')
      publish({ variant: 'success', title: 'PDF report queued', description: 'Download will open in a new tab.' })
    },
    onError: (error: any) => {
      publish({ variant: 'danger', title: 'Unable to generate PDF', description: error?.message })
    },
  })

  const csvMutation = useMutation({
    mutationFn: (payload: { range?: 'last_7d' | 'last_30d' }) => apiClient.generateCSV(payload),
    onSuccess: (data) => {
      window.open(data.downloadUrl, '_blank')
      publish({ variant: 'success', title: 'CSV export ready', description: 'Download will open in a new tab.' })
    },
    onError: (error: any) => {
      publish({ variant: 'danger', title: 'Unable to export CSV', description: error?.message })
    },
  })

  return (
    <div className="space-y-8">
      <PageHeader
        title="Exports"
        description="Generate presentation-ready PDFs or detailed CSV datasets."
      />

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader className="flex items-start gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-danger-100 text-danger-600">
              <FileTextIcon className="h-5 w-5" />
            </span>
            <div>
              <CardTitle>PDF report</CardTitle>
              <CardDescription>Executive-ready summary with KPIs, charts, and ESG metrics.</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Time range</p>
              <Select value={pdfRange} onChange={(value) => setPdfRange(value as 'last_7d' | 'last_30d')} options={rangeOptions} />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Specific lot</p>
              <Select value={selectedLot} onChange={(value) => setSelectedLot(value as string)} options={lotOptions} />
            </div>
            <Button
              className="w-full"
              onClick={() => pdfMutation.mutate({ lotId: selectedLot || undefined, range: pdfRange })}
              loading={pdfMutation.isPending}
            >
              <DownloadIcon className="mr-2 h-4 w-4" /> Generate PDF report
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex items-start gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-success-100 text-success-600">
              <TableIcon className="h-5 w-5" />
            </span>
            <div>
              <CardTitle>CSV export</CardTitle>
              <CardDescription>Raw inspection data with garment, lot, and defect attributes.</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Time range</p>
              <Select value={csvRange} onChange={(value) => setCsvRange(value as 'last_7d' | 'last_30d')} options={rangeOptions} />
            </div>
            <Button
              className="w-full"
              variant="secondary"
              onClick={() => csvMutation.mutate({ range: csvRange })}
              loading={csvMutation.isPending}
            >
              <DownloadIcon className="mr-2 h-4 w-4" /> Export CSV data
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>What’s included</CardTitle>
          <CardDescription>Understand the content and lifecycle of each export.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-neutral-600">
          <div className="flex items-center justify-between border-b border-neutral-200 pb-2">
            <span>PDF bundle</span>
            <span className="font-medium text-neutral-900">KPIs, anomaly charts, defect breakdown, and approval timeline.</span>
          </div>
          <div className="flex items-center justify-between border-b border-neutral-200 pb-2">
            <span>CSV dataset</span>
            <span className="font-medium text-neutral-900">Every inspection with garment, operator, defect status, and timestamps.</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Link policy</span>
            <span className="font-medium text-neutral-900">Downloads remain active for 10 minutes for security.</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
