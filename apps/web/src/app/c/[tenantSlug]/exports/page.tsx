'use client'

import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { apiClient } from '@/lib/api'
import { DownloadIcon, FileTextIcon, TableIcon } from 'lucide-react'

export default function ExportsPage() {
  const [pdfRange, setPdfRange] = useState<'last_7d' | 'last_30d'>('last_7d')
  const [csvRange, setCsvRange] = useState<'last_7d' | 'last_30d'>('last_7d')
  const [selectedLot, setSelectedLot] = useState<string>('')

  const { data: lots = [] } = useQuery({
    queryKey: ['lots'],
    queryFn: () => apiClient.getLots(),
  })

  const pdfMutation = useMutation({
    mutationFn: (payload: { lotId?: string; range?: 'last_7d' | 'last_30d' }) =>
      apiClient.generatePDF(payload),
  })

  const csvMutation = useMutation({
    mutationFn: (payload: { range?: 'last_7d' | 'last_30d' }) =>
      apiClient.generateCSV(payload),
  })

  const handlePdfExport = () => {
    pdfMutation.mutate(
      {
        lotId: selectedLot || undefined,
        range: pdfRange,
      },
      {
        onSuccess: (data) => {
          window.open(data.downloadUrl, '_blank')
        },
      },
    )
  }

  const handleCsvExport = () => {
    csvMutation.mutate(
      {
        range: csvRange,
      },
      {
        onSuccess: (data) => {
          window.open(data.downloadUrl, '_blank')
        },
      },
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Exports</h1>
          <p className="text-sm text-gray-500 mt-1">
            Generate reports and export inspection data
          </p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* PDF Report Export */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center mb-4">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <FileTextIcon className="w-5 h-5 text-red-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">PDF Report</h3>
              <p className="text-sm text-gray-500">Generate a comprehensive QA report</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Time Range
              </label>
              <select
                value={pdfRange}
                onChange={(e) => setPdfRange(e.target.value as 'last_7d' | 'last_30d')}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              >
                <option value="last_7d">Last 7 Days</option>
                <option value="last_30d">Last 30 Days</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Specific Lot (Optional)
              </label>
              <select
                value={selectedLot}
                onChange={(e) => setSelectedLot(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              >
                <option value="">All Lots</option>
                {lots.map((lot: any) => (
                  <option key={lot.id} value={lot.id}>
                    {lot.styleRef} - {lot.factory?.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handlePdfExport}
              disabled={pdfMutation.isPending}
              className="w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors disabled:opacity-50"
            >
              {pdfMutation.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Generating PDF...
                </>
              ) : (
                <>
                  <DownloadIcon className="w-4 h-4 mr-2" />
                  Generate PDF Report
                </>
              )}
            </button>
          </div>
        </div>

        {/* CSV Export */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center mb-4">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <TableIcon className="w-5 h-5 text-green-600" />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-medium text-gray-900">CSV Export</h3>
              <p className="text-sm text-gray-500">Export inspection data as CSV</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Time Range
              </label>
              <select
                value={csvRange}
                onChange={(e) => setCsvRange(e.target.value as 'last_7d' | 'last_30d')}
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              >
                <option value="last_7d">Last 7 Days</option>
                <option value="last_30d">Last 30 Days</option>
              </select>
            </div>

            <button
              onClick={handleCsvExport}
              disabled={csvMutation.isPending}
              className="w-full flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors disabled:opacity-50"
            >
              {csvMutation.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Generating CSV...
                </>
              ) : (
                <>
                  <DownloadIcon className="w-4 h-4 mr-2" />
                  Export CSV Data
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Export History/Status */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Export Information</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <span className="text-sm text-gray-600">PDF includes:</span>
            <span className="text-sm font-medium text-gray-900">KPIs, charts, defect breakdown, recent inspections</span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <span className="text-sm text-gray-600">CSV includes:</span>
            <span className="text-sm font-medium text-gray-900">All inspection records with garment, batch, and defect details</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-gray-600">File expiration:</span>
            <span className="text-sm font-medium text-gray-900">Links expire after 10 minutes</span>
          </div>
        </div>
      </div>
    </div>
  )
}
