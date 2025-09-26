'use client'

import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { X, FileText } from 'lucide-react'
import { ReportType, ReportLanguage } from '@qa-dashboard/shared'

interface ReportGenerationModalProps {
  isOpen: boolean
  onClose: () => void
  onComplete: () => void
  initialType?: ReportType
  initialLotId?: string
}

const REPORT_TYPES = [
  {
    type: ReportType.EXECUTIVE_QUALITY_SUMMARY,
    label: 'Executive Quality Summary',
    description: 'High-level overview of quality metrics and performance',
    requiresLot: false,
    icon: '📊',
  },
  {
    type: ReportType.LOT_INSPECTION_REPORT,
    label: 'Lot Inspection Report',
    description: 'Detailed inspection results for a specific lot',
    requiresLot: true,
    icon: '🔍',
  },
  {
    type: ReportType.MEASUREMENT_COMPLIANCE_SHEET,
    label: 'Measurement Compliance Sheet',
    description: 'Measurement validation and compliance tracking',
    requiresLot: true,
    icon: '📏',
  },
  {
    type: ReportType.PACKAGING_READINESS_REPORT,
    label: 'Packaging & Readiness Report',
    description: 'Packaging validation and readiness status',
    requiresLot: true,
    icon: '📦',
  },
  {
    type: ReportType.SUPPLIER_PERFORMANCE_SNAPSHOT,
    label: 'Supplier Performance Snapshot',
    description: 'Performance metrics across suppliers',
    requiresLot: false,
    icon: '🏭',
  },
  {
    type: ReportType.INLINE_QC_CHECKPOINTS,
    label: 'Inline QC Checkpoints',
    description: 'Quality control checkpoint tracking',
    requiresLot: true,
    icon: '✅',
  },
  {
    type: ReportType.DPP_SUMMARY,
    label: 'DPP Summary',
    description: 'Digital Product Passport summary',
    requiresLot: false,
    icon: '🌱',
  },
]

export function ReportGenerationModal({
  isOpen,
  onClose,
  onComplete,
  initialType,
  initialLotId
}: ReportGenerationModalProps) {
  const [selectedType, setSelectedType] = useState<ReportType>(initialType || ReportType.EXECUTIVE_QUALITY_SUMMARY)
  const [selectedLot, setSelectedLot] = useState<string>(initialLotId || '')
  const [selectedLanguage, setSelectedLanguage] = useState<ReportLanguage>(ReportLanguage.EN)
  const [parameters, setParameters] = useState<Record<string, any>>({})

  const { data: lots = [] } = useQuery({
    queryKey: ['lots'],
    queryFn: () => apiClient.getLots(),
  })

  const generateMutation = useMutation({
    mutationFn: async (data: { type: ReportType; lotId?: string; params: any; language: ReportLanguage }) => {
      switch (data.type) {
        case ReportType.EXECUTIVE_QUALITY_SUMMARY:
          return apiClient.generateExecutiveSummary(data.params, data.language)
        case ReportType.LOT_INSPECTION_REPORT:
          return apiClient.generateLotInspectionReport(data.lotId!, data.params, data.language)
        case ReportType.MEASUREMENT_COMPLIANCE_SHEET:
          return apiClient.generateMeasurementComplianceSheet(data.lotId!, data.params, data.language)
        case ReportType.PACKAGING_READINESS_REPORT:
          return apiClient.generatePackagingReadinessReport(data.lotId!, data.params, data.language)
        case ReportType.SUPPLIER_PERFORMANCE_SNAPSHOT:
          return apiClient.generateSupplierPerformanceSnapshot(data.params, data.language)
        case ReportType.INLINE_QC_CHECKPOINTS:
          return apiClient.generateInlineQcCheckpoints(data.lotId!, data.params, data.language)
        case ReportType.DPP_SUMMARY:
          return apiClient.generateDppSummary(data.params, data.language)
        default:
          throw new Error(`Unsupported report type: ${data.type}`)
      }
    },
    onSuccess: () => {
      onComplete()
    },
  })

  const selectedReportType = REPORT_TYPES.find(rt => rt.type === selectedType)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const params: Record<string, any> = { ...parameters }

    // Add date range for reports that need it
    if (selectedType === ReportType.EXECUTIVE_QUALITY_SUMMARY || selectedType === ReportType.SUPPLIER_PERFORMANCE_SNAPSHOT) {
      const endDate = new Date().toISOString().split('T')[0]
      const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      params.period = { startDate, endDate }
    }

    // Add lot ID for lot-specific reports
    if (selectedReportType?.requiresLot) {
      params.lotId = selectedLot
    }

    generateMutation.mutate({
      type: selectedType,
      lotId: selectedReportType?.requiresLot ? selectedLot : undefined,
      params,
      language: selectedLanguage,
    })
  }

  const handleClose = () => {
    if (!generateMutation.isPending) {
      onClose()
      // Reset form
      setSelectedType(initialType || ReportType.EXECUTIVE_QUALITY_SUMMARY)
      setSelectedLot(initialLotId || '')
      setSelectedLanguage(ReportLanguage.EN)
      setParameters({})
    }
  }

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center">
                    <FileText className="w-6 h-6 text-primary-600 mr-2" />
                    <Dialog.Title as="h3" className="text-lg font-medium text-gray-900">
                      Generate Report
                    </Dialog.Title>
                  </div>
                  <button
                    type="button"
                    className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none"
                    onClick={handleClose}
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Report Type Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Report Type
                    </label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {REPORT_TYPES.map((reportType) => (
                        <div
                          key={reportType.type}
                          className={`relative cursor-pointer rounded-lg border p-4 hover:bg-gray-50 ${
                            selectedType === reportType.type
                              ? 'border-primary-500 ring-2 ring-primary-500 bg-primary-50'
                              : 'border-gray-300'
                          }`}
                          onClick={() => setSelectedType(reportType.type)}
                        >
                          <div className="flex items-start">
                            <div className="text-2xl mr-3">{reportType.icon}</div>
                            <div className="flex-1">
                              <h4 className="text-sm font-medium text-gray-900">
                                {reportType.label}
                              </h4>
                              <p className="text-xs text-gray-500 mt-1">
                                {reportType.description}
                              </p>
                            </div>
                          </div>
                          {selectedType === reportType.type && (
                            <div className="absolute top-2 right-2">
                              <div className="w-2 h-2 bg-primary-600 rounded-full"></div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Lot Selection (if required) */}
                  {selectedReportType?.requiresLot && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Select Lot *
                      </label>
                      <select
                        value={selectedLot}
                        onChange={(e) => setSelectedLot(e.target.value)}
                        required
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                      >
                        <option value="">Choose a lot...</option>
                        {lots.map((lot: any) => (
                          <option key={lot.id} value={lot.id}>
                            {lot.styleRef} - {lot.factory?.name} ({lot.quantityTotal} units)
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Language Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Language
                    </label>
                    <select
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(e.target.value as ReportLanguage)}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    >
                      <option value={ReportLanguage.EN}>English</option>
                      <option value={ReportLanguage.PT}>Portuguese</option>
                      <option value={ReportLanguage.ES}>Spanish</option>
                    </select>
                  </div>

                  {/* Additional Parameters */}
                  {selectedType === ReportType.LOT_INSPECTION_REPORT && (
                    <div className="space-y-4">
                      <h4 className="text-sm font-medium text-gray-700">Report Options</h4>
                      <div className="space-y-2">
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={parameters.includePhotos !== false}
                            onChange={(e) => setParameters(prev => ({ ...prev, includePhotos: e.target.checked }))}
                            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span className="ml-2 text-sm text-gray-700">Include photos</span>
                        </label>
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={parameters.includeDefectDetails !== false}
                            onChange={(e) => setParameters(prev => ({ ...prev, includeDefectDetails: e.target.checked }))}
                            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span className="ml-2 text-sm text-gray-700">Include defect details</span>
                        </label>
                      </div>
                    </div>
                  )}

                  {selectedType === ReportType.MEASUREMENT_COMPLIANCE_SHEET && (
                    <div className="space-y-4">
                      <h4 className="text-sm font-medium text-gray-700">Report Options</h4>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={parameters.includeMeasurementImages !== false}
                          onChange={(e) => setParameters(prev => ({ ...prev, includeMeasurementImages: e.target.checked }))}
                          className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        />
                        <span className="ml-2 text-sm text-gray-700">Include measurement images</span>
                      </label>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                    <button
                      type="button"
                      onClick={handleClose}
                      disabled={generateMutation.isPending}
                      className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={generateMutation.isPending || (selectedReportType?.requiresLot && !selectedLot)}
                      className="px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md shadow-sm disabled:opacity-50"
                    >
                      {generateMutation.isPending ? 'Generating...' : 'Generate Report'}
                    </button>
                  </div>
                </form>

                {generateMutation.error && (
                  <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm text-red-600">
                      Failed to generate report: {generateMutation.error.message}
                    </p>
                  </div>
                )}

                {generateMutation.isSuccess && (
                  <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
                    <p className="text-sm text-green-600">
                      Report generation started successfully! You can view the progress on the reports page.
                    </p>
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}