'use client'

import { useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Image from 'next/image'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/components/providers/auth-provider'
import { LotHeader } from '@/components/lots/lot-header'
import { LotApprovalModal } from '@/components/lots/lot-approval-modal'
import { LotFormModal } from '@/components/lots/lot-form-modal'
import { formatDate, formatPercentage, formatNumber } from '@/lib/utils'
import { SupplyChainStageStatus, UserRole, ReportType } from '@qa-dashboard/shared'
import { ReportGenerationModal } from '@/components/reports/report-generation-modal'
import { FileTextIcon, PlusIcon, DownloadIcon } from 'lucide-react'

const SUPPLY_CHAIN_STATUS_META: Record<
  SupplyChainStageStatus,
  { label: string; badge: string; dot: string }
> = {
  [SupplyChainStageStatus.NOT_STARTED]: {
    label: 'Not started',
    badge: 'bg-gray-100 text-gray-600',
    dot: 'bg-gray-300 border-gray-300',
  },
  [SupplyChainStageStatus.IN_PROGRESS]: {
    label: 'In progress',
    badge: 'bg-sky-100 text-sky-700',
    dot: 'bg-sky-500 border-sky-500',
  },
  [SupplyChainStageStatus.COMPLETED]: {
    label: 'Completed',
    badge: 'bg-green-100 text-green-700',
    dot: 'bg-green-500 border-green-500',
  },
}

export default function LotDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showApproveModal, setShowApproveModal] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showReportModal, setShowReportModal] = useState(false)

  const lotId = params.id as string

  const { data: lot, isLoading } = useQuery({
    queryKey: ['lot', lotId],
    queryFn: () => apiClient.getLot(lotId),
  })

  const { data: lotReports = [] } = useQuery({
    queryKey: ['lot-reports', lotId],
    queryFn: async () => {
      const allReports = await apiClient.getReports()
      return allReports.filter((report: any) => report.lotId === lotId)
    },
  })

  const approveMutation = useMutation({
    mutationFn: (note?: string) => apiClient.approveLot(lotId, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lot', lotId] })
      queryClient.invalidateQueries({ queryKey: ['lots'] })
      setShowApproveModal(false)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (note: string) => apiClient.rejectLot(lotId, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lot', lotId] })
      queryClient.invalidateQueries({ queryKey: ['lots'] })
      setShowRejectModal(false)
    },
  })

  const advanceMutation = useMutation({
    mutationFn: () => apiClient.advanceLotSupplyChain(lotId),
    onSuccess: (updatedLot) => {
      queryClient.setQueryData(['lot', lotId], updatedLot)
      queryClient.invalidateQueries({ queryKey: ['lots'] })
    },
  })

  const downloadReportMutation = useMutation({
    mutationFn: async (reportId: string) => {
      const blob = await apiClient.downloadReport(reportId)
      const report = lotReports.find((r: any) => r.id === reportId)

      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = report?.fileName || `report-${reportId}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    },
  })

  const supplyChainTimeline = useMemo(() => {
    if (!lot?.suppliers) {
      return [] as Array<{
        id: string
        supplierName: string
        roleName: string
        supplierSequence: number
        sequence: number
        status: SupplyChainStageStatus
        startedAt?: string | null
        completedAt?: string | null
        co2Kg?: number | null
      }>
    }

    return lot.suppliers
      .slice()
      .sort((a, b) => a.sequence - b.sequence)
      .flatMap((supplier) =>
        (supplier.roles ?? [])
          .slice()
          .sort((a, b) => a.sequence - b.sequence)
          .map((role) => ({
            id: role.id,
            supplierName: supplier.factory?.name ?? 'Supplier',
            roleName: role.role?.name ?? 'Stage',
            supplierSequence: supplier.sequence,
            sequence: role.sequence,
            status: (role.status as SupplyChainStageStatus) ?? SupplyChainStageStatus.NOT_STARTED,
            startedAt: role.startedAt ?? null,
            completedAt: role.completedAt ?? null,
            co2Kg: role.co2Kg != null ? Number(role.co2Kg) : null,
          })),
      );
  }, [lot]);

  const currentStageIndex = supplyChainTimeline.findIndex(
    (stage) => stage.status === SupplyChainStageStatus.IN_PROGRESS,
  );
  const currentStage = currentStageIndex >= 0 ? supplyChainTimeline[currentStageIndex] : undefined;
  const nextStage = (() => {
    if (currentStageIndex >= 0) {
      return supplyChainTimeline
        .slice(currentStageIndex + 1)
        .find((stage) => stage.status !== SupplyChainStageStatus.COMPLETED);
    }
    return supplyChainTimeline.find((stage) => stage.status !== SupplyChainStageStatus.COMPLETED);
  })();
  const supplyChainComplete =
    supplyChainTimeline.length > 0 &&
    supplyChainTimeline.every((stage) => stage.status === SupplyChainStageStatus.COMPLETED);

  const canManage = user?.roles?.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role)) ?? false
  const canApprove = Boolean(canManage && lot?.status === 'PENDING_APPROVAL')

  if (isLoading || !lot) {
    return (
      <div className="space-y-6">
        <button onClick={() => router.back()} className="text-gray-500 hover:text-gray-700 font-medium">
          ← Back
        </button>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  const inspections = lot.inspections || []
  const approvals = lot.approvals || []
  const suppliers = lot.suppliers?.slice().sort((a, b) => a.sequence - b.sequence) ?? []
  const primarySupplier = suppliers.find((supplier) => supplier.isPrimary)?.factory ?? lot.factory
  const supplierHelper = suppliers.length > 1
    ? `${suppliers.length} factories in chain`
    : [primarySupplier?.city, primarySupplier?.country].filter(Boolean).join(', ') || '—'
  const materialComposition = lot.materialComposition || []
  const certifications = lot.certifications || []
  const dppMetadata = lot.dppMetadata
  const sustainabilityHighlights = dppMetadata?.sustainabilityHighlights || []

  const handleApprove = (note: string) => approveMutation.mutate(note || undefined)
  const handleReject = (note: string) => rejectMutation.mutate(note)

  const handleReportGenerated = () => {
    queryClient.invalidateQueries({ queryKey: ['lot-reports', lotId] })
    queryClient.invalidateQueries({ queryKey: ['reports'] })
    setShowReportModal(false)
  }

  const handleDownloadReport = (reportId: string) => {
    downloadReportMutation.mutate(reportId)
  }

  return (
    <div className="space-y-6">
      <button onClick={() => router.back()} className="text-gray-500 hover:text-gray-700 font-medium">
        ← Back to Lots
      </button>

      <LotHeader
        lot={lot}
        canApprove={canApprove}
        canEdit={canManage}
        onApprove={() => setShowApproveModal(true)}
        onReject={() => setShowRejectModal(true)}
        onEdit={() => setShowEditModal(true)}
      />

      <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard label="Primary factory" value={primarySupplier?.name || 'Unassigned'} helper={supplierHelper} />
        <StatCard label="Quantity" value={lot.quantityTotal.toLocaleString()} helper="Units in lot" />
        <StatCard label="Progress" value={formatPercentage(lot.inspectedProgress)} helper="Inspection coverage" />
        <StatCard label="Defect Rate" value={formatPercentage(lot.defectRate)} helper="Last update" />
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Supply Chain Progress</h3>
            <p className="text-sm text-gray-500">
              Track each factory stage from fiber prep to finishing. Advance as production hands off to the next team.
            </p>
            {currentStage && (
              <p className="mt-1 text-xs text-gray-500">
                Current stage: <span className="font-medium text-gray-800">{currentStage.roleName}</span> @{' '}
                {currentStage.supplierName}
              </p>
            )}
          </div>
          {canManage && supplyChainTimeline.length > 0 && !supplyChainComplete && (
            <button
              onClick={() => advanceMutation.mutate()}
              disabled={advanceMutation.isPending}
              className="inline-flex items-center rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 disabled:opacity-60"
            >
              {advanceMutation.isPending
                ? 'Advancing…'
                : `Advance to ${nextStage?.roleName ?? 'completion'}`}
            </button>
          )}
        </div>
        <div className="p-6">
          {advanceMutation.isError && (
            <div className="mb-4 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              Failed to advance stage. Try again.
            </div>
          )}
          {supplyChainTimeline.length === 0 ? (
            <p className="text-sm text-gray-500">
              Configure supply-chain roles for this lot to visualize hand-offs between factories.
            </p>
          ) : (
            <ol className="relative ml-3 border-l border-gray-200">
              {supplyChainTimeline.map((stage) => {
                const meta = SUPPLY_CHAIN_STATUS_META[stage.status];
                return (
                  <li key={stage.id} className="relative mb-8 ml-4 last:mb-0">
                    <span
                      className={`absolute -left-6 top-1 h-4 w-4 rounded-full border ${meta.dot}`}
                    ></span>
                    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                      <div>
                        <h4 className="text-sm font-semibold text-gray-900">{stage.roleName}</h4>
                        <p className="text-xs text-gray-500">{stage.supplierName}</p>
                      </div>
                      <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${meta.badge}`}>
                        {meta.label}
                      </span>
                    </div>
                    <div className="mt-2 space-y-1 text-xs text-gray-500">
                      {stage.startedAt && <p>Started {formatDate(stage.startedAt)}</p>}
                      {stage.completedAt && <p>Completed {formatDate(stage.completedAt)}</p>}
                      {typeof stage.co2Kg === 'number' && stage.co2Kg > 0 && (
                        <p>CO₂ contribution · {stage.co2Kg.toFixed(2)} kg</p>
                      )}
                    </div>
                  </li>
                )
              })}
            </ol>
          )}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Inspection Timeline</h3>
          <p className="text-sm text-gray-500">Full history of inspections, defects, and photographic evidence.</p>
        </div>
        <div className="divide-y divide-gray-200">
          {inspections.length === 0 && (
            <div className="p-6 text-sm text-gray-500">No inspections recorded yet.</div>
          )}
          {inspections.map((inspection) => (
            <div key={inspection.id} className="p-6">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
                <div>
                  <h4 className="text-md font-semibold text-gray-900">Inspection {inspection.id.substring(0, 8)}</h4>
                  <p className="text-sm text-gray-500">
                    {inspection.inspectorId
                      ? `Inspector: ${inspection.inspectorId}`
                      : 'Inspector pending assignment'}
                  </p>
                </div>
                <div className="text-sm text-gray-500">
                  Started {inspection.startedAt ? formatDate(inspection.startedAt) : 'N/A'}
                  {inspection.finishedAt && ` · Finished ${formatDate(inspection.finishedAt)}`}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {(inspection.defects || []).map((defect) => (
                  <div key={defect.id} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="text-sm font-medium text-gray-900">{defect.defectTypeId || 'Observation'}</span>
                        {defect.pieceCode && (
                          <p className="text-xs text-gray-500">Piece: {defect.pieceCode}</p>
                        )}
                      </div>
                      <span className="text-xs text-gray-500">{formatDate(defect.createdAt)}</span>
                    </div>
                    {defect.note && <p className="text-sm text-gray-700 mb-3">{defect.note}</p>}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {(defect.photos || []).map((photo) => (
                        <figure key={photo.id} className="bg-white rounded border border-gray-200 overflow-hidden">
                          <Image
                            src={photo.url}
                            alt="Inspection evidence"
                            className="w-full h-40 object-cover"
                            width={400}
                            height={160}
                            sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                          />
                          {photo.annotation && (
                            <figcaption className="px-3 py-2 text-xs text-gray-600">
                              {photo.annotation.comment}
                            </figcaption>
                          )}
                        </figure>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Approval History</h3>
        </div>
        <div className="p-6 space-y-4">
          {approvals.length === 0 && (
            <p className="text-sm text-gray-500">No approval decisions recorded yet.</p>
          )}
          {approvals.map((approval) => (
            <div key={approval.id} className="flex items-start space-x-3">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  approval.decision === 'APPROVE' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                }`}
              >
                {approval.decision === 'APPROVE' ? '✓' : '✕'}
              </div>
              <div className="flex-1">
                <div className="text-sm text-gray-900 font-medium">
                  {approval.decision === 'APPROVE' ? 'Approved' : 'Rejected'}
                </div>
                <div className="text-xs text-gray-500">{formatDate(approval.decidedAt)}</div>
                {approval.note && <p className="text-sm text-gray-700 mt-2">{approval.note}</p>}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Reports</h3>
            <p className="text-sm text-gray-500">Generate and view reports for this lot</p>
          </div>
          {canManage && (
            <button
              onClick={() => setShowReportModal(true)}
              className="inline-flex items-center rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700"
            >
              <PlusIcon className="w-4 h-4 mr-2" />
              Generate Report
            </button>
          )}
        </div>
        <div className="p-6">
          {lotReports.length === 0 ? (
            <div className="text-center py-8">
              <FileTextIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h4 className="text-sm font-medium text-gray-900 mb-2">No reports yet</h4>
              <p className="text-sm text-gray-500 mb-4">
                Generate detailed reports for inspections, compliance, and packaging readiness
              </p>
              {canManage && (
                <button
                  onClick={() => setShowReportModal(true)}
                  className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md"
                >
                  <PlusIcon className="w-4 h-4 mr-2" />
                  Generate First Report
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {lotReports.map((report: any) => (
                <div key={report.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-gray-900">{report.fileName}</h4>
                    <div className="flex items-center space-x-4 text-xs text-gray-500 mt-1">
                      <span>Created {formatDate(report.createdAt)}</span>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        report.status === 'COMPLETED' || report.status === 'READY'
                          ? 'bg-green-100 text-green-800'
                          : report.status === 'GENERATING'
                          ? 'bg-blue-100 text-blue-800'
                          : report.status === 'FAILED'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {report.status}
                      </span>
                    </div>
                  </div>
                  {(report.status === 'COMPLETED' || report.status === 'READY') && (
                    <button
                      onClick={() => handleDownloadReport(report.id)}
                      disabled={downloadReportMutation.isPending}
                      className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                    >
                      <DownloadIcon className="w-3 h-3 mr-1" />
                      Download
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">DPP Hub</h3>
            <p className="text-sm text-gray-500">
              Traceability, sustainability and compliance data prepared for the EU Digital Product Passport.
            </p>
          </div>
        </div>
        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="border border-gray-200 rounded-lg p-4 space-y-2">
            <h4 className="font-semibold text-gray-900">Passport Overview</h4>
            {dppMetadata ? (
              <div className="space-y-2 text-gray-600">
                <p><span className="font-medium text-gray-800">ID:</span> {dppMetadata.dppId || '—'}</p>
                <p><span className="font-medium text-gray-800">Version:</span> {dppMetadata.version || '—'}</p>
                {dppMetadata.status && (
                  <p>
                    <span className="font-medium text-gray-800">Status:</span> {dppMetadata.status}
                  </p>
                )}
                {dppMetadata.lastAudit && (
                  <p>
                    <span className="font-medium text-gray-800">Last audit:</span> {formatDate(dppMetadata.lastAudit)}
                  </p>
                )}
                {typeof dppMetadata.traceabilityScore === 'number' && (
                  <p>
                    <span className="font-medium text-gray-800">Traceability score:</span> {formatNumber(dppMetadata.traceabilityScore)}%
                  </p>
                )}
                {typeof dppMetadata.co2FootprintKg === 'number' && (
                  <p>
                    <span className="font-medium text-gray-800">Total CO₂:</span> {dppMetadata.co2FootprintKg.toFixed(1)} kg
                  </p>
                )}
                {dppMetadata.publicUrl && (
                  <a
                    href={dppMetadata.publicUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center rounded-md border border-primary-200 bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700 hover:bg-primary-100"
                  >
                    Open passport
                  </a>
                )}
                {sustainabilityHighlights.length > 0 && (
                  <div className="pt-2 border-t border-gray-200">
                    <p className="font-medium text-gray-800">Highlights</p>
                    <ul className="mt-1 space-y-1 text-xs text-gray-600">
                      {sustainabilityHighlights.map((item, index) => (
                        <li key={`${item}-${index}`}>• {item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500">Passport data not captured yet.</p>
            )}
          </div>
          <div className="border border-gray-200 rounded-lg p-4 space-y-2">
            <h4 className="font-semibold text-gray-900">Material Composition</h4>
            {materialComposition.length > 0 ? (
              <ul className="space-y-1 text-gray-600">
                {materialComposition.map((component, index) => (
                  <li key={`${component.fiber}-${index}`}>
                    • {component.fiber} {component.percentage}%
                    {component.properties?.region && ` · ${component.properties.region}`}
                  </li>
                ))}
                {lot.dyeLot && <li>• Dye lot: {lot.dyeLot}</li>}
              </ul>
            ) : (
              <p className="text-gray-500">Awaiting material breakdown from suppliers.</p>
            )}
          </div>
          <div className="border border-gray-200 rounded-lg p-4 space-y-2">
            <h4 className="font-semibold text-gray-900">Certifications</h4>
            {certifications.length > 0 ? (
              <ul className="space-y-1 text-gray-600">
                {certifications.map((cert, index) => (
                  <li key={`${cert.type}-${index}`}>
                    • {cert.type.replace(/_/g, ' ')}
                    {cert.number && ` · ${cert.number}`}
                    {cert.validUntil && ` · valid until ${formatDate(cert.validUntil)}`}
                    {cert.auditLink && (
                      <a
                        href={cert.auditLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-2 text-primary-600 hover:text-primary-700"
                      >
                        audit
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">Add supplier certifications to unlock the DPP.</p>
            )}
          </div>
        </div>
      </section>

      <LotApprovalModal
        isOpen={showApproveModal}
        onClose={() => setShowApproveModal(false)}
        onApprove={handleApprove}
        isLoading={approveMutation.isPending}
        type="approve"
      />

      <LotApprovalModal
        isOpen={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        onApprove={handleReject}
        isLoading={rejectMutation.isPending}
        type="reject"
      />

      <LotFormModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        initialLot={lot}
      />

      <ReportGenerationModal
        isOpen={showReportModal}
        onClose={() => setShowReportModal(false)}
        onSuccess={handleReportGenerated}
        initialType={ReportType.LOT_INSPECTION_REPORT}
        initialLotId={lotId}
      />
    </div>
  )
}

function StatCard({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="text-2xl font-semibold text-gray-900 mt-1">{value}</div>
      {helper && <div className="text-xs text-gray-500 mt-1">{helper}</div>}
    </div>
  )
}
