'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LineChartIcon, TrendingDownIcon, TrendingUpIcon, LeafIcon, RecycleIcon, FactoryIcon } from 'lucide-react'
import { useParams, useRouter } from 'next/navigation'

export default function ImpactDashboardPage() {
  const params = useParams()
  const router = useRouter()
  const tenantSlug = params?.tenantSlug as string

  const { data, isLoading } = useQuery({
    queryKey: ['esg-impact-dashboard'],
    queryFn: () => apiClient.getESGImpactDashboard(),
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
          title="ESG Impact Dashboard"
          description="Real-time sustainability metrics and environmental impact tracking"
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
  const trend = data?.trend || []

  const metrics = [
    {
      label: 'Total Pieces Inspected',
      value: summary.totalPieces?.toLocaleString() || '0',
      icon: FactoryIcon,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: 'Defect Rate',
      value: `${summary.defectRate || 0}%`,
      trend: summary.defectRate < 3 ? 'down' : 'up',
      icon: TrendingDownIcon,
      color: summary.defectRate < 3 ? 'text-green-600' : 'text-red-600',
      bgColor: summary.defectRate < 3 ? 'bg-green-50' : 'bg-red-50',
      footer: `${summary.totalDefects || 0} defects found`,
    },
    {
      label: 'Material Efficiency',
      value: `${summary.materialEfficiency?.toFixed(1) || 0}%`,
      trend: summary.materialEfficiency > 95 ? 'up' : 'down',
      icon: RecycleIcon,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      footer: `${summary.rejectedPieces || 0} pieces rejected`,
    },
    {
      label: 'Carbon Footprint',
      value: `${summary.carbonFootprintKg?.toFixed(0) || 0} kg CO₂`,
      icon: LeafIcon,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
      footer: `${summary.wasteKg?.toFixed(1) || 0} kg textile waste`,
    },
  ]

  return (
    <div className="space-y-8">
      <PageHeader
        title="ESG Impact Dashboard"
        description="Real-time sustainability metrics and environmental impact tracking"
        actions={headerActions}
      />

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metric.icon
          const TrendIcon = metric.trend === 'up' ? TrendingUpIcon : TrendingDownIcon
          return (
            <Card key={metric.label}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardDescription>{metric.label}</CardDescription>
                <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${metric.bgColor}`}>
                  <Icon className={`h-5 w-5 ${metric.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-baseline gap-2">
                  <div className="text-2xl font-bold text-neutral-900">{metric.value}</div>
                  {metric.trend && (
                    <TrendIcon
                      className={`h-4 w-4 ${
                        metric.trend === 'down' && metric.label.includes('Defect') ? 'text-green-600' : metric.trend === 'up' && metric.label.includes('Efficiency') ? 'text-green-600' : 'text-red-600'
                      }`}
                    />
                  )}
                </div>
                {metric.footer && (
                  <p className="mt-1 text-xs text-neutral-500">{metric.footer}</p>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Monthly Trend */}
      <Card>
        <CardHeader>
          <CardTitle>6-Month Trend</CardTitle>
          <CardDescription>Quality and environmental performance over time</CardDescription>
        </CardHeader>
        <CardContent>
          {trend.length === 0 ? (
            <div className="text-center py-8 text-neutral-500">
              No historical data available. Data will accumulate over time.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-7 gap-2 text-xs font-medium text-neutral-500 border-b pb-2">
                <div>Month</div>
                <div className="text-right">Pieces</div>
                <div className="text-right">Defect %</div>
                <div className="text-right">Waste (kg)</div>
                <div className="text-right">CO₂ (kg)</div>
                <div className="text-right">Efficiency %</div>
                <div></div>
              </div>
              {trend.map((item: any) => (
                <div key={item.month} className="grid grid-cols-7 gap-2 text-sm items-center">
                  <div className="font-medium text-neutral-900">{item.month}</div>
                  <div className="text-right text-neutral-700">{item.pieces.toLocaleString()}</div>
                  <div className={`text-right font-semibold ${item.defectRate < 3 ? 'text-green-600' : 'text-red-600'}`}>
                    {item.defectRate}%
                  </div>
                  <div className="text-right text-neutral-700">{item.wasteKg}</div>
                  <div className="text-right text-neutral-700">{item.co2Kg}</div>
                  <div className={`text-right font-semibold ${item.materialEfficiency > 95 ? 'text-green-600' : 'text-amber-600'}`}>
                    {item.materialEfficiency}%
                  </div>
                  <div className="text-right">
                    {item.defectRate < 3 && item.materialEfficiency > 95 && (
                      <span className="text-green-600 text-xs">✓ Target met</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Compliance Status */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>ISO 14001 Environmental</CardTitle>
            <CardDescription>Material efficiency and waste management</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-600">Status:</span>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  summary.materialEfficiency > 95 ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                }`}>
                  {summary.materialEfficiency > 95 ? 'Compliant' : 'Needs Review'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-600">Target:</span>
                <span className="text-sm font-medium text-neutral-900">≥ 95% efficiency</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-600">Current:</span>
                <span className="text-sm font-bold text-neutral-900">{summary.materialEfficiency?.toFixed(1)}%</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>ISO 9001 Quality</CardTitle>
            <CardDescription>Defect rate and quality management</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-600">Status:</span>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  summary.defectRate < 5 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {summary.defectRate < 5 ? 'Compliant' : 'Action Required'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-600">Target:</span>
                <span className="text-sm font-medium text-neutral-900">≤ 5% defects</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-neutral-600">Current:</span>
                <span className="text-sm font-bold text-neutral-900">{summary.defectRate?.toFixed(2)}%</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Certification Status */}
      <Card className="bg-gradient-to-r from-primary-50 to-blue-50 border-primary-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircleIcon className="h-5 w-5 text-primary-600" />
            Factory Certification Coverage
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="text-4xl font-bold text-primary-600">{summary.certificationRate?.toFixed(0) || 0}%</div>
            <div className="text-sm text-neutral-700">
              of factories have sustainability certifications (GOTS, OEKO-TEX, FSC, PEFC, etc.)
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}