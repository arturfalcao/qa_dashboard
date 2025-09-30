'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LeafIcon, AlertTriangleIcon, TrendingDownIcon } from 'lucide-react'
import { useParams, useRouter } from 'next/navigation'

export default function CarbonFootprintPage() {
  const params = useParams()
  const router = useRouter()
  const tenantSlug = params?.tenantSlug as string

  const { data, isLoading } = useQuery({
    queryKey: ['esg-carbon-footprint'],
    queryFn: () => apiClient.getCarbonFootprint(),
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
          title="Carbon Footprint Analysis"
          description="Monitor CO₂ emissions from waste and production across supply chain"
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

  const summary = data?.summary || {}
  const monthlyData = data?.monthlyBreakdown || []
  const recommendations = data?.recommendations || []

  return (
    <div className="space-y-8">
      <PageHeader
        title="Carbon Footprint Analysis"
        description="Monitor CO₂ emissions from waste and production across your supply chain"
        actions={headerActions}
      />

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardDescription>Total CO₂ Emissions</CardDescription>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50">
              <LeafIcon className="h-5 w-5 text-red-600" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{summary.totalCo2Kg?.toFixed(0) || 0} kg</div>
            <p className="text-xs text-neutral-500 mt-1">Across all operations</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardDescription>From Quality Defects</CardDescription>
            <AlertTriangleIcon className="h-5 w-5 text-amber-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-600">{summary.co2FromWaste?.toFixed(0) || 0} kg</div>
            <p className="text-xs text-neutral-500 mt-1">{summary.wasteKg?.toFixed(1) || 0} kg textile waste</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardDescription>From Production (DPP)</CardDescription>
            <LeafIcon className="h-5 w-5 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{summary.co2FromProduction?.toFixed(0) || 0} kg</div>
            <p className="text-xs text-neutral-500 mt-1">Reported in DPP data</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardDescription>CO₂ per Piece</CardDescription>
            <TrendingDownIcon className="h-5 w-5 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{(summary.co2PerPiece * 1000)?.toFixed(1) || 0} g</div>
            <p className="text-xs text-neutral-500 mt-1">Per garment inspected</p>
          </CardContent>
        </Card>
      </div>

      {/* Monthly Trend */}
      <Card>
        <CardHeader>
          <CardTitle>Monthly Carbon Emissions</CardTitle>
          <CardDescription>CO₂ footprint from defects and waste over time</CardDescription>
        </CardHeader>
        <CardContent>
          {monthlyData.length === 0 ? (
            <div className="text-center py-8 text-neutral-500">
              No historical data available. Emissions will be tracked as data accumulates.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-5 gap-2 text-xs font-medium text-neutral-500 border-b pb-2">
                <div>Month</div>
                <div className="text-right">Pieces</div>
                <div className="text-right">Waste (kg)</div>
                <div className="text-right">CO₂ (kg)</div>
                <div className="text-right">Trend</div>
              </div>
              {monthlyData.map((item: any, index: number) => {
                const prevCo2 = index > 0 ? monthlyData[index - 1].co2Kg : item.co2Kg
                const trend = item.co2Kg < prevCo2 ? 'down' : item.co2Kg > prevCo2 ? 'up' : 'flat'
                const trendColor = trend === 'down' ? 'text-green-600' : trend === 'up' ? 'text-red-600' : 'text-neutral-500'
                const trendIcon = trend === 'down' ? '↓' : trend === 'up' ? '↑' : '→'

                return (
                  <div key={item.month} className="grid grid-cols-5 gap-2 text-sm items-center">
                    <div className="font-medium text-neutral-900">{item.month}</div>
                    <div className="text-right text-neutral-700">{item.pieces.toLocaleString()}</div>
                    <div className="text-right text-amber-600 font-semibold">{item.wasteKg} kg</div>
                    <div className="text-right text-red-600 font-bold">{item.co2Kg} kg</div>
                    <div className={`text-right font-semibold ${trendColor}`}>
                      {trendIcon} {index > 0 ? `${Math.abs(((item.co2Kg - prevCo2) / prevCo2 * 100)).toFixed(0)}%` : '—'}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Breakdown */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Emission Sources</CardTitle>
            <CardDescription>Breakdown of total carbon footprint</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-neutral-700">Quality Defects & Waste</span>
                  <span className="text-sm font-bold text-red-600">
                    {((summary.co2FromWaste / (summary.totalCo2Kg || 1)) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-500"
                    style={{ width: `${(summary.co2FromWaste / (summary.totalCo2Kg || 1)) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-neutral-500 mt-1">
                  {summary.co2FromWaste?.toFixed(0) || 0} kg CO₂ from {summary.wasteKg?.toFixed(1) || 0} kg rejected garments
                </p>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-neutral-700">Production (DPP Tracked)</span>
                  <span className="text-sm font-bold text-green-600">
                    {((summary.co2FromProduction / (summary.totalCo2Kg || 1)) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500"
                    style={{ width: `${(summary.co2FromProduction / (summary.totalCo2Kg || 1)) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-neutral-500 mt-1">
                  {summary.co2FromProduction?.toFixed(0) || 0} kg CO₂ from manufacturing (Digital Product Passport data)
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Carbon Intensity</CardTitle>
            <CardDescription>Emissions efficiency metrics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-neutral-50">
              <div>
                <div className="text-sm text-neutral-600">CO₂ per piece</div>
                <div className="text-xs text-neutral-500 mt-1">Lower is better</div>
              </div>
              <div className="text-2xl font-bold text-neutral-900">
                {(summary.co2PerPiece * 1000)?.toFixed(1) || 0}g
              </div>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-neutral-50">
              <div>
                <div className="text-sm text-neutral-600">Total pieces</div>
                <div className="text-xs text-neutral-500 mt-1">Inspected</div>
              </div>
              <div className="text-2xl font-bold text-neutral-900">
                {summary.totalPieces?.toLocaleString() || 0}
              </div>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-amber-50">
              <div>
                <div className="text-sm text-amber-900">Waste factor</div>
                <div className="text-xs text-amber-700 mt-1">5kg CO₂ per kg waste</div>
              </div>
              <div className="text-sm font-medium text-amber-900">
                Industry standard
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-blue-900">
              <LeafIcon className="h-5 w-5" />
              Carbon Reduction Recommendations
            </CardTitle>
            <CardDescription>Actions to reduce your carbon footprint</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {recommendations.map((rec: string, index: number) => (
                <li key={index} className="flex items-start gap-3">
                  <span className="flex-shrink-0 mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
                    {index + 1}
                  </span>
                  <span className="text-sm text-blue-900">{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Methodology */}
      <Card className="bg-neutral-50">
        <CardHeader>
          <CardTitle>Calculation Methodology</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-neutral-700">
          <div>
            <strong>Quality Defect Emissions:</strong> Each rejected garment = 0.2kg average weight × 5kg CO₂ per kg textile waste = 1kg CO₂ per rejected piece.
          </div>
          <div>
            <strong>Production Emissions:</strong> Tracked via Digital Product Passport (DPP) metadata when available. Includes raw material extraction, dyeing, finishing, and manufacturing.
          </div>
          <div>
            <strong>Reduction Potential:</strong> Every 1% improvement in defect rate reduces waste proportionally. Example: 1% defect reduction in 10,000 pieces = 100 pieces saved = 20kg material = 100kg CO₂ avoided.
          </div>
          <div className="pt-2 border-t">
            <strong>Industry Benchmark:</strong> Apparel industry average carbon footprint is 5-15kg CO₂ per garment. Quality defects add unnecessary emissions on top of baseline production impact.
          </div>
        </CardContent>
      </Card>

      {/* Call to Action */}
      <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
        <CardContent className="py-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100 flex-shrink-0">
              <LeafIcon className="h-6 w-6 text-green-600" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-green-900 mb-2">Reduce Your Carbon Impact</h3>
              <p className="text-sm text-green-800 mb-3">
                Quality control directly impacts environmental sustainability. By reducing defects, you simultaneously improve
                profitability, customer satisfaction, and environmental performance.
              </p>
              <Button
                size="sm"
                className="bg-green-600 hover:bg-green-700 text-white"
                onClick={() => router.push(`/c/${tenantSlug}/esg-reports/factory-scorecard`)}
              >
                View Factory Performance
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}