'use client'

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Factory, UserRole } from '@qa-dashboard/shared'
import { FactoryFormModal } from '@/components/factories/factory-form-modal'
import { useAuth } from '@/components/providers/auth-provider'
import { formatDate } from '@/lib/utils'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { EmptyState } from '@/components/ui/empty-state'
import { FactoryIcon, MapPinIcon } from 'lucide-react'

export default function FactoriesPage() {
  const { user } = useAuth()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingFactory, setEditingFactory] = useState<Factory | null>(null)

  const canEdit = user?.roles?.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role)) ?? false

  const { data: factories = [], isLoading } = useQuery({
    queryKey: ['factories'],
    queryFn: () => apiClient.getFactories(),
  })

  const summary = useMemo(() => {
    const total = factories.length
    const certified = factories.filter((factory) => (factory.certifications ?? []).length > 0).length
    const withCapabilities = factories.filter((factory) => (factory.capabilities ?? []).length > 0).length
    const countries = new Set(factories.map((factory) => factory.country).filter(Boolean))

    return { total, certified, withCapabilities, countries: countries.size }
  }, [factories])

  const openModal = (factory?: Factory | null) => {
    setEditingFactory(factory ?? null)
    setIsModalOpen(true)
  }

  const pageActions = canEdit ? (
    <Button onClick={() => openModal(null)}>Add factory</Button>
  ) : undefined

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Factories"
          description="Manage the production facilities available to your team."
          actions={pageActions}
        />
        <Card>
          <CardContent className="flex h-48 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Factories"
        description="Manage the production facilities available to your team."
        actions={pageActions}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Total factories</CardDescription>
            <CardTitle>{summary.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>With certifications</CardDescription>
            <CardTitle>{summary.certified}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Documented capabilities</CardDescription>
            <CardTitle>{summary.withCapabilities}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Countries represented</CardDescription>
            <CardTitle>{summary.countries}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <CardTitle>Factory directory</CardTitle>
            <CardDescription>Location, certifications, and onboarding dates.</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {factories.length === 0 ? (
            <EmptyState
              icon={<FactoryIcon className="h-5 w-5" />}
              title="No factories yet"
              description={
                canEdit
                  ? 'Start by adding a factory to plan production lots.'
                  : 'No factories have been configured for your workspace yet.'
              }
              action={canEdit ? { label: 'Add factory', onClick: () => openModal(null) } : undefined}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Certifications</TableHead>
                  <TableHead>Created</TableHead>
                  {canEdit && <TableHead className="text-right">Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {factories.map((factory) => (
                  <TableRow key={factory.id}>
                    <TableCell>
                      <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                        {factory.name}
                      </div>
                      {factory.capabilities && factory.capabilities.length > 0 && (
                        <p className="text-xs text-neutral-500">
                          {(factory.capabilities
                            ?.map((capability) => capability.role?.name)
                            .filter(Boolean) as string[]
                          ).join(', ')}
                        </p>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
                        <MapPinIcon className="h-4 w-4 text-neutral-400" />
                        {[factory.city, factory.country].filter(Boolean).join(', ') || '—'}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm text-neutral-700 dark:text-neutral-300">
                      {(factory.certifications ?? []).length > 0
                        ? `${factory.certifications?.length} certificate${factory.certifications?.length === 1 ? '' : 's'}`
                        : '—'}
                    </TableCell>
                    <TableCell className="text-sm text-neutral-500">
                      {formatDate(factory.createdAt)}
                    </TableCell>
                    {canEdit && (
                      <TableCell className="text-right">
                        <Button variant="secondary" size="sm" onClick={() => openModal(factory)}>
                          Edit
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <FactoryFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        initialFactory={editingFactory}
      />
    </div>
  )
}
