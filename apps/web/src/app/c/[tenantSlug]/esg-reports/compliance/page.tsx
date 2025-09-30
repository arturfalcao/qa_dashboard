'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CheckCircleIcon, AlertCircleIcon, FileTextIcon, DownloadIcon } from 'lucide-react'
import { useParams, useRouter } from 'next/navigation'

export default function ComplianceSummaryPage() {
  const params = useParams()
  const router = useRouter()
  const tenantSlug = params?.tenantSlug as string

  const { data, isLoading } = useQuery({
    queryKey: ['esg-compliance-summary'],
    queryFn: () => apiClient.getComplianceSummary(),
  })

  const headerActions = (
    <div className="flex gap-2">
      <Button variant="secondary" size="sm" onClick={() => window.print()}>
        <DownloadIcon className="h-4 w-4 mr-2" />
        Print Report
      </Button>
      <Button variant="secondary" size="sm" onClick={() => router.push(`/c/${tenantSlug}/esg-reports`)}>
        ← All Reports
      </Button>
    </div>
  )

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="ISO Compliance Summary"
          description="Audit-ready reports for ISO 9001 (Quality) and ISO 14001 (Environmental)"
          actions={headerActions}
        />
        <Card>
          <CardContent className="flex h-48 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600" />
          </CardContent>
        </Card>
      </div>
    )
  }

  const iso9001 = data?.iso9001 || {}
  const iso14001 = data?.iso14001 || {}
  const certifications = data?.certifications || []

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLIANT':
        return { label: 'Compliant', class: 'bg-green-100 text-green-700', icon: CheckCircleIcon }
      case 'REVIEW_REQUIRED':
        return { label: 'Review Required', class: 'bg-amber-100 text-amber-700', icon: AlertCircleIcon }
      case 'IMPROVEMENT_NEEDED':
        return { label: 'Improvement Needed', class: 'bg-red-100 text-red-700', icon: AlertCircleIcon }
      default:
        return { label: 'Unknown', class: 'bg-neutral-100 text-neutral-700', icon: FileTextIcon }
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="ISO Compliance Summary"
        description="Audit-ready reports for ISO 9001 (Quality) and ISO 14001 (Environmental) standards"
        actions={headerActions}
      />

      {/* Report Metadata */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-neutral-600">Report Generated</div>
              <div className="text-lg font-semibold text-neutral-900">
                {data?.generatedAt ? new Date(data.generatedAt).toLocaleString() : 'N/A'}
              </div>
            </div>
            <div className="flex items-center gap-2 text-blue-600">
              <FileTextIcon className="h-5 w-5" />
              <span className="font-medium">Audit Ready</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ISO 9001 - Quality Management */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl">{iso9001.standard}</CardTitle>
              <CardDescription>{iso9001.category}</CardDescription>
            </div>
            {iso9001.status && (() => {
              const badge = getStatusBadge(iso9001.status)
              const Icon = badge.icon
              return (
                <div className={`flex items-center gap-2 rounded-full px-4 py-2 ${badge.class}`}>
                  <Icon className="h-4 w-4" />
                  <span className="font-semibold">{badge.label}</span>
                </div>
              )
            })()}
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 mb-3">Key Metrics</h3>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-neutral-200 p-4">
                <div className="text-2xl font-bold text-neutral-900">{iso9001.metrics?.totalLots || 0}</div>
                <div className="text-sm text-neutral-600 mt-1">Total Lots</div>
              </div>
              <div className="rounded-lg border border-neutral-200 p-4">
                <div className="text-2xl font-bold text-green-600">{iso9001.metrics?.approvedLots || 0}</div>
                <div className="text-sm text-neutral-600 mt-1">Approved</div>
              </div>
              <div className="rounded-lg border border-neutral-200 p-4">
                <div className="text-2xl font-bold text-red-600">{iso9001.metrics?.rejectedLots || 0}</div>
                <div className="text-sm text-neutral-600 mt-1">Rejected</div>
              </div>
              <div className="rounded-lg border border-neutral-200 p-4">
                <div className={`text-2xl font-bold ${(iso9001.metrics?.avgDefectRate || 0) < 5 ? 'text-green-600' : 'text-red-600'}`}>
                  {iso9001.metrics?.avgDefectRate?.toFixed(2) || 0}%
                </div>
                <div className="text-sm text-neutral-600 mt-1">Avg Defect Rate</div>
              </div>
            </div>
          </div>

          <div className="rounded-lg bg-neutral-50 p-4">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-1">
                {(iso9001.metrics?.avgDefectRate || 0) < 5 ? (
                  <CheckCircleIcon className="h-5 w-5 text-green-600" />
                ) : (
                  <AlertCircleIcon className="h-5 w-5 text-amber-600" />
                )}
              </div>
              <div className="flex-1">
                <div className="font-semibold text-neutral-900 mb-1">Approval Rate</div>
                <div className="text-sm text-neutral-700">
                  {iso9001.metrics?.approvalRate || 0}% of lots approved.
                  {(iso9001.metrics?.approvalRate || 0) >= 90 ? (
                    <span className="text-green-600 font-medium"> Exceeds ISO 9001 quality targets.</span>
                  ) : (
                    <span className="text-amber-600 font-medium"> Review quality control processes.</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-neutral-900 mb-2">Compliance Assessment</h3>
            <div className="text-sm text-neutral-700 space-y-2">
              <p>
                <strong>Target:</strong> Average defect rate ≤ 5% to maintain compliance with ISO 9001:2015 quality management standards.
              </p>
              <p>
                <strong>Current Performance:</strong> {iso9001.metrics?.avgDefectRate?.toFixed(2) || 0}% average defect rate across {iso9001.metrics?.totalLots || 0} lots.
              </p>
              {(iso9001.metrics?.avgDefectRate || 0) >= 5 && (
                <p className="text-amber-700 bg-amber-50 p-3 rounded-lg">
                  ⚠️ <strong>Action Required:</strong> Defect rate exceeds target. Review operator training, implement preventive measures, and increase inline inspections.
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ISO 14001 - Environmental Management */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl">{iso14001.standard}</CardTitle>
              <CardDescription>{iso14001.category}</CardDescription>
            </div>
            {iso14001.status && (() => {
              const badge = getStatusBadge(iso14001.status)
              const Icon = badge.icon
              return (
                <div className={`flex items-center gap-2 rounded-full px-4 py-2 ${badge.class}`}>
                  <Icon className="h-4 w-4" />
                  <span className="font-semibold">{badge.label}</span>
                </div>
              )
            })()}
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-neutral-900 mb-3">Environmental Impact Metrics</h3>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-neutral-200 p-4">
                <div className="text-2xl font-bold text-neutral-900">{iso14001.metrics?.totalPieces?.toLocaleString() || 0}</div>
                <div className="text-sm text-neutral-600 mt-1">Total Pieces</div>
              </div>
              <div className="rounded-lg border border-neutral-200 p-4">
                <div className="text-2xl font-bold text-red-600">{iso14001.metrics?.rejectedPieces?.toLocaleString() || 0}</div>
                <div className="text-sm text-neutral-600 mt-1">Rejected</div>
              </div>
              <div className="rounded-lg border border-neutral-200 p-4">
                <div className="text-2xl font-bold text-amber-600">{iso14001.metrics?.wasteKg?.toFixed(1) || 0} kg</div>
                <div className="text-sm text-neutral-600 mt-1">Textile Waste</div>
              </div>
              <div className="rounded-lg border border-neutral-200 p-4">
                <div className="text-2xl font-bold text-green-600">{iso14001.metrics?.co2Kg?.toFixed(0) || 0} kg</div>
                <div className="text-sm text-neutral-600 mt-1">CO₂ Emissions</div>
              </div>
            </div>
          </div>

          <div className="rounded-lg bg-emerald-50 p-4">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-1">
                <CheckCircleIcon className="h-5 w-5 text-emerald-600" />
              </div>
              <div className="flex-1">
                <div className="font-semibold text-neutral-900 mb-1">Waste Reduction Rate</div>
                <div className="text-sm text-neutral-700">
                  {iso14001.metrics?.wasteReductionRate || 0}% of pieces pass quality control, demonstrating effective environmental management and resource efficiency.
                </div>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-neutral-900 mb-2">Environmental Compliance</h3>
            <div className="text-sm text-neutral-700 space-y-2">
              <p>
                <strong>Target:</strong> Minimize waste and carbon emissions through quality control. Target ≥97% material efficiency (≤3% defect rate).
              </p>
              <p>
                <strong>Carbon Footprint:</strong> {iso14001.metrics?.co2Kg?.toFixed(2) || 0} kg CO₂ from rejected garments (avg 5kg CO₂ per kg textile waste).
              </p>
              <p>
                <strong>Improvement Opportunities:</strong> Each 1% reduction in defect rate saves approximately{' '}
                {(((iso14001.metrics?.totalPieces || 0) * 0.01 * 0.2 * 5) || 0).toFixed(0)} kg CO₂ emissions.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Certifications Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Factory Certification Coverage</CardTitle>
          <CardDescription>Sustainability certifications across supply chain</CardDescription>
        </CardHeader>
        <CardContent>
          {certifications.length === 0 ? (
            <div className="text-center py-8 text-neutral-500">
              <FileTextIcon className="h-12 w-12 mx-auto mb-4 text-neutral-400" />
              <p>No certification data available.</p>
              <p className="text-sm mt-2">Add factory certifications to track compliance coverage.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {certifications.map((cert: any) => (
                <div
                  key={cert.type}
                  className="flex items-center justify-between rounded-lg border border-neutral-200 p-4"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100">
                      <FileTextIcon className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <div className="font-semibold text-neutral-900">{cert.type}</div>
                      <div className="text-sm text-neutral-600">
                        {cert.count} {cert.count === 1 ? 'factory' : 'factories'}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-neutral-900">{cert.percentage}%</div>
                    <div className="text-xs text-neutral-500">coverage</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Audit Trail Note */}
      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <FileTextIcon className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-900">
              <strong>Audit Trail:</strong> This report is automatically generated from your quality inspection data.
              All metrics are traceable to individual lot inspections, providing complete transparency for ISO auditors.
              Export this report during certification audits or include in sustainability disclosures.
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}