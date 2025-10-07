'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, useMemo } from 'react'
import { apiClient } from '@/lib/api'
import { DownloadIcon, FileTextIcon, TableIcon, FileSpreadsheetIcon, DatabaseIcon } from 'lucide-react'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Select, SelectOption } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { useToast } from '@/components/ui/toast'

export default function ExportsPage() {
  const [csvRange, setCsvRange] = useState<'last_7d' | 'last_30d'>('last_7d')
  const { publish } = useToast()

  const rangeOptions: SelectOption<'last_7d' | 'last_30d'>[] = [
    { value: 'last_7d', label: 'Last 7 days' },
    { value: 'last_30d', label: 'Last 30 days' },
  ]

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
        title="Data Exports"
        description="Export your production data in various formats for analysis, reporting, and integration with other systems."
      />

      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="flex items-start gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-success-100 text-success-600">
              <TableIcon className="h-5 w-5" />
            </span>
            <div>
              <CardTitle>CSV Export</CardTitle>
              <CardDescription>Raw inspection data in CSV format for Excel, Google Sheets, or data analysis tools.</CardDescription>
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
              <DownloadIcon className="mr-2 h-4 w-4" /> Export to CSV
            </Button>
            <div className="text-xs text-gray-500 mt-2">
              Includes: lots, inspections, defects, timestamps, factory info, and quality metrics.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex items-start gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              <FileSpreadsheetIcon className="h-5 w-5" />
            </span>
            <div>
              <CardTitle>Excel Export</CardTitle>
              <CardDescription>Formatted workbook with multiple sheets for lots, inspections, and analytics.</CardDescription>
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
              onClick={() => {
                publish({ variant: 'info', title: 'Coming Soon', description: 'Excel export will be available soon.' })
              }}
              disabled
            >
              <DownloadIcon className="mr-2 h-4 w-4" /> Export to Excel
            </Button>
            <div className="text-xs text-gray-500 mt-2">
              Multiple sheets: Lots, Inspections, Defects, Supply Chain, Analytics Summary.
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex items-start gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 text-purple-600">
              <DatabaseIcon className="h-5 w-5" />
            </span>
            <div>
              <CardTitle>JSON Export</CardTitle>
              <CardDescription>Structured data in JSON format for API integration and custom applications.</CardDescription>
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
              onClick={() => {
                publish({ variant: 'info', title: 'Coming Soon', description: 'JSON export will be available soon.' })
              }}
              disabled
            >
              <DownloadIcon className="mr-2 h-4 w-4" /> Export to JSON
            </Button>
            <div className="text-xs text-gray-500 mt-2">
              Complete data structure with nested relationships and metadata.
            </div>
          </CardContent>
        </Card>

      </div>

      <Card>
        <CardHeader>
          <CardTitle>Export Use Cases</CardTitle>
          <CardDescription>How you can use exported data in your workflows</CardDescription>
        </CardHeader>
        <CardContent className="grid md:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <div className="font-semibold text-gray-900">CSV Format</div>
            <ul className="space-y-1 text-gray-600 list-disc list-inside">
              <li>Import into Excel or Google Sheets for custom analysis</li>
              <li>Load into business intelligence tools (Power BI, Tableau)</li>
              <li>Process with Python/R for statistical analysis</li>
              <li>Share raw data with supply chain partners</li>
            </ul>
          </div>
          <div className="space-y-2">
            <div className="font-semibold text-gray-900">Excel Format</div>
            <ul className="space-y-1 text-gray-600 list-disc list-inside">
              <li>Pre-formatted sheets ready for presentations</li>
              <li>Pivot tables and charts already configured</li>
              <li>Multiple worksheets for different data types</li>
              <li>Compatible with Microsoft Office and LibreOffice</li>
            </ul>
          </div>
          <div className="space-y-2">
            <div className="font-semibold text-gray-900">JSON Format</div>
            <ul className="space-y-1 text-gray-600 list-disc list-inside">
              <li>Integrate with custom applications and dashboards</li>
              <li>Feed data into ERP/MRP systems via API</li>
              <li>Build automated workflows and notifications</li>
              <li>Archive complete data snapshots</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Data Security</CardTitle>
          <CardDescription>How we protect your exported data</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-neutral-600">
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5 flex-shrink-0"></div>
            <div>
              <div className="font-medium text-gray-900">Time-limited download links</div>
              <div className="text-gray-600">Download links expire after 10 minutes for security</div>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5 flex-shrink-0"></div>
            <div>
              <div className="font-medium text-gray-900">Tenant isolation</div>
              <div className="text-gray-600">Only your tenant&apos;s data is included in exports</div>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5 flex-shrink-0"></div>
            <div>
              <div className="font-medium text-gray-900">Audit trail</div>
              <div className="text-gray-600">All exports are logged for compliance and security monitoring</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
