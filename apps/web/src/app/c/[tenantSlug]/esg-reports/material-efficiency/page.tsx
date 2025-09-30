'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RecycleIcon, TrendingUpIcon, TrendingDownIcon, PackageIcon } from 'lucide-react'
import { useParams, useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'

export default function MaterialEfficiencyPage() {
  const params = useParams()
  const router = useRouter()
  const tenantSlug = params?.tenantSlug as string

  const { data, isLoading } = useQuery({
    queryKey: ['esg-material-efficiency'],
    queryFn: () => apiClient.getMaterialEfficiency(),
  })

  const headerActions = (
    <Button variant="secondary" size="sm" onClick={() => router.push(`/c/${tenantSlug}/esg-reports`)}>
      ← All Reports
    </Button>
  )

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Material Efficiency Report"
          description="Track waste reduction, material usage, and efficiency improvements"
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

  const overview = data?.overview || {}
  const lots = data?.lots || []

  const highEfficiencyLots = lots.filter((lot: any) => lot.materialEfficiency >= 95)
  const lowEfficiencyLots = lots.filter((lot: any) => lot.materialEfficiency < 90)

  return (
    <div className="space-y-8">
      <PageHeader
        title="Material Efficiency Report"
        description="Track waste reduction, material usage, and efficiency improvements across all lots"
        actions={headerActions}
      />

      {/* Overview Metrics */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardDescription>Total Pieces</CardDescription>
            <PackageIcon className="h-4 w-4 text-neutral-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-neutral-900">{overview.totalPieces?.toLocaleString() || 0}</div>
            <p className="text-xs text-neutral-500 mt-1">Across all lots</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardDescription>Accepted Pieces</CardDescription>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50">
              <TrendingUpIcon className="h-5 w-5 text-green-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{overview.acceptedPieces?.toLocaleString() || 0}</div>
            <p className="text-xs text-neutral-500 mt-1">Passed quality control</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardDescription>Rejected Pieces</CardDescription>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50">
              <TrendingDownIcon className="h-5 w-5 text-red-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{overview.rejectedPieces?.toLocaleString() || 0}</div>
            <p className="text-xs text-neutral-500 mt-1">{overview.wasteKg?.toFixed(1) || 0} kg waste</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardDescription>Overall Efficiency</CardDescription>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50">
              <RecycleIcon className="h-5 w-5 text-purple-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className={cn(
              'text-2xl font-bold',
              (overview.overallEfficiency || 0) >= 95 ? 'text-green-600' : (overview.overallEfficiency || 0) >= 90 ? 'text-amber-600' : 'text-red-600'
            )}>
              {overview.overallEfficiency?.toFixed(1) || 0}%
            </div>
            <p className="text-xs text-neutral-500 mt-1">
              {(overview.overallEfficiency || 0) >= 95 ? '✓ Excellent' : (overview.overallEfficiency || 0) >= 90 ? '⚠️ Good' : '❌ Needs improvement'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* High Performers */}
      {highEfficiencyLots.length > 0 && (
        <Card className="border-green-200 bg-green-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-900">
              <TrendingUpIcon className="h-5 w-5" />
              High Efficiency Lots (≥95%)
            </CardTitle>
            <CardDescription>Lots demonstrating excellent material usage</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2">
              {highEfficiencyLots.slice(0, 6).map((lot: any) => (
                <div
                  key={lot.lotId}
                  className="bg-white rounded-lg p-4 border border-green-200"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-neutral-900">{lot.styleRef}</div>
                      <div className="text-sm text-neutral-600 mt-1">
                        {lot.client} • {lot.factory}
                      </div>
                    </div>
                    <span className="text-lg font-bold text-green-600">{lot.materialEfficiency}%</span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <div className="text-neutral-500">Total</div>
                      <div className="font-medium text-neutral-900">{lot.totalPieces}</div>
                    </div>
                    <div>
                      <div className="text-neutral-500">Accepted</div>
                      <div className="font-medium text-green-600">{lot.acceptedPieces}</div>
                    </div>
                    <div>
                      <div className="text-neutral-500">Defect Rate</div>
                      <div className="font-medium text-neutral-900">{lot.defectRate}%</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Full Lot Table */}
      <Card>
        <CardHeader>
          <CardTitle>Material Efficiency by Lot</CardTitle>
          <CardDescription>Detailed breakdown of material usage and waste per lot</CardDescription>
        </CardHeader>
        <CardContent>
          {lots.length === 0 ? (
            <div className="text-center py-12 text-neutral-500">
              <RecycleIcon className="h-12 w-12 mx-auto mb-4 text-neutral-400" />
              <p>No lot data available yet.</p>
              <p className="text-sm mt-2">Start inspecting lots to track material efficiency.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Lot / Style Ref</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Factory</TableHead>
                    <TableHead className="text-right">Total Pieces</TableHead>
                    <TableHead className="text-right">Accepted</TableHead>
                    <TableHead className="text-right">Rejected</TableHead>
                    <TableHead className="text-right">Defect Rate</TableHead>
                    <TableHead className="text-right">Efficiency</TableHead>
                    <TableHead className="text-right">Waste (kg)</TableHead>
                    <TableHead className="text-right">CO₂ (kg)</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lots.map((lot: any) => (
                    <TableRow key={lot.lotId}>
                      <TableCell className="font-medium text-neutral-900">{lot.styleRef}</TableCell>
                      <TableCell className="text-sm text-neutral-600">{lot.client || '—'}</TableCell>
                      <TableCell className="text-sm text-neutral-600">{lot.factory || '—'}</TableCell>
                      <TableCell className="text-right text-neutral-900">{lot.totalPieces}</TableCell>
                      <TableCell className="text-right text-green-600 font-semibold">{lot.acceptedPieces}</TableCell>
                      <TableCell className="text-right text-red-600 font-semibold">{lot.rejectedPieces}</TableCell>
                      <TableCell className="text-right">
                        <span className={cn(
                          'font-semibold',
                          lot.defectRate < 3 ? 'text-green-600' : lot.defectRate < 5 ? 'text-amber-600' : 'text-red-600'
                        )}>
                          {lot.defectRate}%
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={cn(
                          'font-bold',
                          lot.materialEfficiency >= 95 ? 'text-green-600' : lot.materialEfficiency >= 90 ? 'text-amber-600' : 'text-red-600'
                        )}>
                          {lot.materialEfficiency}%
                        </span>
                      </TableCell>
                      <TableCell className="text-right text-neutral-700">{lot.wasteKg}</TableCell>
                      <TableCell className="text-right text-neutral-700">{lot.co2Kg}</TableCell>
                      <TableCell>
                        <span className={cn(
                          'inline-flex rounded-full px-2 py-0.5 text-xs font-semibold',
                          lot.status === 'APPROVED' ? 'bg-green-100 text-green-700' :
                          lot.status === 'REJECTED' ? 'bg-red-100 text-red-700' :
                          lot.status === 'PENDING_APPROVAL' ? 'bg-amber-100 text-amber-700' :
                          'bg-neutral-100 text-neutral-700'
                        )}>
                          {lot.status.replace('_', ' ')}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Low Efficiency Alert */}
      {lowEfficiencyLots.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-900">
              <TrendingDownIcon className="h-5 w-5" />
              Low Efficiency Alert (&lt;90%)
            </CardTitle>
            <CardDescription>Lots requiring immediate attention to reduce waste</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {lowEfficiencyLots.map((lot: any) => (
                <div
                  key={lot.lotId}
                  className="bg-white rounded-lg p-4 border border-red-200"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-neutral-900">{lot.styleRef}</div>
                      <div className="text-sm text-neutral-600 mt-1">
                        {lot.client} • {lot.factory}
                      </div>
                      <div className="mt-2 text-sm text-red-700">
                        ⚠️ <strong>{lot.rejectedPieces}</strong> pieces rejected ({lot.wasteKg} kg waste, {lot.co2Kg} kg CO₂)
                      </div>
                    </div>
                    <span className="text-lg font-bold text-red-600">{lot.materialEfficiency}%</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Card */}
      <Card className="bg-neutral-50">
        <CardHeader>
          <CardTitle>Material Efficiency Insights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-neutral-700">
          <div>
            <strong>Average Waste per Lot:</strong> {overview.avgWastePerLot || 0} kg of textile waste generated per lot.
          </div>
          <div>
            <strong>Total Environmental Impact:</strong> {overview.wasteKg?.toFixed(1) || 0} kg textile waste produced {overview.co2Kg?.toFixed(0) || 0} kg of CO₂ emissions.
          </div>
          <div>
            <strong>Efficiency Target:</strong> Aim for ≥95% material efficiency (≤5% defect rate) to minimize waste and meet environmental standards.
          </div>
          <div className="pt-2 border-t">
            <strong>Cost Savings Opportunity:</strong> If all lots achieved 95% efficiency, you would save approximately{' '}
            {(((overview.totalPieces || 0) * 0.01 * 0.2) || 0).toFixed(1)} kg of material waste.
          </div>
        </CardContent>
      </Card>
    </div>
  )
}