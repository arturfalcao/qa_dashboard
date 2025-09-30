'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { FactoryIcon, AwardIcon, MapPinIcon, TrendingUpIcon } from 'lucide-react'
import { useParams, useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'

export default function FactoryScorecardPage() {
  const params = useParams()
  const router = useRouter()
  const tenantSlug = params?.tenantSlug as string

  const { data: scorecard = [], isLoading } = useQuery({
    queryKey: ['factory-esg-scorecard'],
    queryFn: () => apiClient.getFactoryESGScorecard(),
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
          title="Factory ESG Scorecard"
          description="Compare factory performance on quality, environmental, and compliance metrics"
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

  const topPerformers = scorecard.slice(0, 3)
  const needsImprovement = scorecard.filter((f: any) => f.scores.esg < 60)

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-amber-600'
    return 'text-red-600'
  }

  const getScoreBadge = (score: number) => {
    if (score >= 80) return { label: 'Excellent', class: 'bg-green-100 text-green-700' }
    if (score >= 60) return { label: 'Good', class: 'bg-amber-100 text-amber-700' }
    return { label: 'Needs Improvement', class: 'bg-red-100 text-red-700' }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Factory ESG Scorecard"
        description="Compare factory performance on quality, environmental, and compliance metrics"
        actions={headerActions}
      />

      {/* Top Performers */}
      {topPerformers.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-4 flex items-center gap-2">
            <AwardIcon className="h-5 w-5 text-amber-500" />
            Top Performing Factories
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            {topPerformers.map((factory: any, index: number) => {
              const badge = getScoreBadge(factory.scores.esg)
              return (
                <Card key={factory.factoryId} className="relative overflow-hidden">
                  {index === 0 && (
                    <div className="absolute top-0 right-0">
                      <div className="bg-amber-400 text-white px-3 py-1 text-xs font-bold rounded-bl-lg">
                        🏆 #1
                      </div>
                    </div>
                  )}
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-base">{factory.factoryName}</CardTitle>
                        <CardDescription className="flex items-center gap-1 mt-1">
                          <MapPinIcon className="h-3 w-3" />
                          {factory.city}, {factory.country}
                        </CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-neutral-600">Overall ESG Score</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-2xl font-bold ${getScoreColor(factory.scores.esg)}`}>
                          {factory.scores.esg}
                        </span>
                        <span className="text-neutral-400 text-sm">/100</span>
                      </div>
                    </div>
                    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${badge.class}`}>
                      {badge.label}
                    </span>
                    <div className="grid grid-cols-2 gap-2 pt-2 border-t text-xs">
                      <div>
                        <div className="text-neutral-500">Quality</div>
                        <div className="font-semibold text-neutral-900">{factory.scores.quality}/100</div>
                      </div>
                      <div>
                        <div className="text-neutral-500">Environmental</div>
                        <div className="font-semibold text-neutral-900">{factory.scores.environmental}/100</div>
                      </div>
                      <div>
                        <div className="text-neutral-500">Efficiency</div>
                        <div className="font-semibold text-neutral-900">{factory.scores.materialEfficiency}/100</div>
                      </div>
                      <div>
                        <div className="text-neutral-500">Compliance</div>
                        <div className="font-semibold text-neutral-900">{factory.scores.compliance}/100</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      )}

      {/* Full Scorecard Table */}
      <Card>
        <CardHeader>
          <CardTitle>Complete Factory Rankings</CardTitle>
          <CardDescription>All factories ranked by overall ESG score (Quality 30% + Efficiency 30% + Compliance 20% + Environmental 20%)</CardDescription>
        </CardHeader>
        <CardContent>
          {scorecard.length === 0 ? (
            <div className="text-center py-12 text-neutral-500">
              <FactoryIcon className="h-12 w-12 mx-auto mb-4 text-neutral-400" />
              <p>No factory data available yet.</p>
              <p className="text-sm mt-2">Start inspecting lots to populate factory performance metrics.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">Rank</TableHead>
                    <TableHead>Factory</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead className="text-center">ESG Score</TableHead>
                    <TableHead className="text-center">Quality</TableHead>
                    <TableHead className="text-center">Efficiency</TableHead>
                    <TableHead className="text-center">Compliance</TableHead>
                    <TableHead className="text-center">Environmental</TableHead>
                    <TableHead>Certifications</TableHead>
                    <TableHead className="text-right">Lots</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {scorecard.map((factory: any, index: number) => {
                    const badge = getScoreBadge(factory.scores.esg)
                    return (
                      <TableRow key={factory.factoryId}>
                        <TableCell className="font-medium text-neutral-500">
                          {index === 0 && '🏆'}
                          {index === 1 && '🥈'}
                          {index === 2 && '🥉'}
                          {index > 2 && `#${index + 1}`}
                        </TableCell>
                        <TableCell className="font-medium text-neutral-900">
                          {factory.factoryName}
                        </TableCell>
                        <TableCell className="text-sm text-neutral-600">
                          {factory.city}, {factory.country}
                        </TableCell>
                        <TableCell className="text-center">
                          <div className="flex flex-col items-center gap-1">
                            <span className={`text-lg font-bold ${getScoreColor(factory.scores.esg)}`}>
                              {factory.scores.esg}
                            </span>
                            <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${badge.class}`}>
                              {badge.label}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          <span className={cn('font-semibold', getScoreColor(factory.scores.quality))}>
                            {factory.scores.quality}
                          </span>
                        </TableCell>
                        <TableCell className="text-center">
                          <span className={cn('font-semibold', getScoreColor(factory.scores.materialEfficiency))}>
                            {factory.scores.materialEfficiency}
                          </span>
                        </TableCell>
                        <TableCell className="text-center">
                          <span className={cn('font-semibold', getScoreColor(factory.scores.compliance))}>
                            {factory.scores.compliance}
                          </span>
                        </TableCell>
                        <TableCell className="text-center">
                          <span className={cn('font-semibold', getScoreColor(factory.scores.environmental))}>
                            {factory.scores.environmental}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {factory.certifications.length === 0 ? (
                              <span className="text-xs text-neutral-400">None</span>
                            ) : (
                              factory.certifications.slice(0, 3).map((cert: any) => (
                                <span
                                  key={cert.id}
                                  className="inline-flex rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700"
                                >
                                  {cert.type}
                                </span>
                              ))
                            )}
                            {factory.certifications.length > 3 && (
                              <span className="text-xs text-neutral-500">
                                +{factory.certifications.length - 3} more
                              </span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right text-sm text-neutral-600">
                          {factory.metrics.totalLots}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Improvement Opportunities */}
      {needsImprovement.length > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-900">
              <TrendingUpIcon className="h-5 w-5" />
              Improvement Opportunities
            </CardTitle>
            <CardDescription>Factories scoring below 60 need targeted interventions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {needsImprovement.map((factory: any) => (
                <div
                  key={factory.factoryId}
                  className="bg-white rounded-lg p-4 border border-amber-200"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-neutral-900">{factory.factoryName}</div>
                      <div className="text-sm text-neutral-600 mt-1">
                        {factory.city}, {factory.country}
                      </div>
                    </div>
                    <span className="text-lg font-bold text-red-600">{factory.scores.esg}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    {factory.scores.quality < 60 && (
                      <span className="rounded bg-red-100 px-2 py-1 text-red-700">
                        ⚠️ Quality: {factory.scores.quality} (Defect rate: {factory.metrics.defectRate}%)
                      </span>
                    )}
                    {factory.scores.materialEfficiency < 60 && (
                      <span className="rounded bg-amber-100 px-2 py-1 text-amber-700">
                        ⚠️ Efficiency: {factory.scores.materialEfficiency}
                      </span>
                    )}
                    {factory.scores.compliance < 40 && (
                      <span className="rounded bg-purple-100 px-2 py-1 text-purple-700">
                        ⚠️ Compliance: {factory.scores.compliance} ({factory.metrics.certifications} certs)
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Scoring Methodology */}
      <Card className="bg-neutral-50">
        <CardHeader>
          <CardTitle>Scoring Methodology</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-neutral-700">
          <div>
            <strong>Quality Score (30%):</strong> Based on defect rate. Lower defects = higher score. Target: &lt;5% defects.
          </div>
          <div>
            <strong>Material Efficiency (30%):</strong> Percentage of pieces accepted. Target: ≥95% efficiency.
          </div>
          <div>
            <strong>Compliance Score (20%):</strong> Number of sustainability certifications (GOTS, OEKO-TEX, FSC, PEFC, etc.). 20 points per certification.
          </div>
          <div>
            <strong>Environmental Score (20%):</strong> CO₂ emissions per piece from waste. Lower carbon = higher score.
          </div>
          <div className="pt-2 border-t">
            <strong>Overall ESG Score = </strong> (Quality × 0.3) + (Efficiency × 0.3) + (Compliance × 0.2) + (Environmental × 0.2)
          </div>
        </CardContent>
      </Card>
    </div>
  )
}