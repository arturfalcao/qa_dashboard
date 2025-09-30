'use client'

import { useParams, useRouter } from 'next/navigation'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  LineChartIcon,
  FactoryIcon,
  CheckCircleIcon,
  RecycleIcon,
  LeafIcon,
  ArrowRightIcon
} from 'lucide-react'

export default function ESGReportsPage() {
  const params = useParams()
  const router = useRouter()
  const tenantSlug = params?.tenantSlug as string

  const reports = [
    {
      id: 'impact-dashboard',
      title: 'ESG Impact Dashboard',
      description: 'Real-time sustainability metrics and environmental impact tracking',
      icon: LineChartIcon,
      href: `/c/${tenantSlug}/esg-reports/impact-dashboard`,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
    },
    {
      id: 'factory-scorecard',
      title: 'Factory ESG Scorecard',
      description: 'Compare factory performance on quality, environmental, and compliance metrics',
      icon: FactoryIcon,
      href: `/c/${tenantSlug}/esg-reports/factory-scorecard`,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      id: 'compliance',
      title: 'ISO Compliance Summary',
      description: 'Audit-ready reports for ISO 9001 (Quality) and ISO 14001 (Environmental)',
      icon: CheckCircleIcon,
      href: `/c/${tenantSlug}/esg-reports/compliance`,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      id: 'material-efficiency',
      title: 'Material Efficiency Report',
      description: 'Track waste reduction, material usage, and efficiency improvements',
      icon: RecycleIcon,
      href: `/c/${tenantSlug}/esg-reports/material-efficiency`,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
    },
    {
      id: 'carbon-footprint',
      title: 'Carbon Footprint Analysis',
      description: 'Monitor CO₂ emissions from waste and production across supply chain',
      icon: LeafIcon,
      href: `/c/${tenantSlug}/esg-reports/carbon-footprint`,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
  ]

  return (
    <div className="space-y-8">
      <PageHeader
        title="ESG Reports"
        description="Comprehensive sustainability, quality, and compliance reporting for ESG managers and auditors."
      />

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {reports.map((report) => {
          const Icon = report.icon
          return (
            <Card
              key={report.id}
              className="group cursor-pointer transition hover:shadow-lg hover:border-primary-200"
              onClick={() => router.push(report.href)}
            >
              <CardHeader className="space-y-4">
                <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${report.bgColor}`}>
                  <Icon className={`h-6 w-6 ${report.color}`} />
                </div>
                <div>
                  <CardTitle className="text-lg flex items-center justify-between">
                    {report.title}
                    <ArrowRightIcon className="h-5 w-5 text-neutral-400 transition group-hover:translate-x-1 group-hover:text-primary-600" />
                  </CardTitle>
                  <CardDescription className="mt-2">{report.description}</CardDescription>
                </div>
              </CardHeader>
            </Card>
          )
        })}
      </div>

      <Card className="bg-gradient-to-r from-primary-50 to-blue-50 border-primary-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LeafIcon className="h-5 w-5 text-primary-600" />
            Why ESG Reporting Matters
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-neutral-700">
          <p>
            <strong>Regulatory Compliance:</strong> Meet ISO 14001 environmental management and ISO 9001 quality standards with automated audit trails.
          </p>
          <p>
            <strong>Customer Demands:</strong> Fashion brands require detailed sustainability data for Digital Product Passports (DPP) and ESG disclosures.
          </p>
          <p>
            <strong>Cost Reduction:</strong> Lower defect rates mean less waste, reduced carbon emissions, and significant material cost savings.
          </p>
          <p>
            <strong>Competitive Advantage:</strong> Demonstrate environmental leadership to win contracts with sustainability-focused brands.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}