'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/components/providers/auth-provider'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { TechPackUploadModal } from '@/components/tech-packs/tech-pack-upload-modal'
import { UserRole } from '@qa-dashboard/shared'
import { formatDate, formatRelativeTime } from '@/lib/utils'
import {
  FileText,
  Upload,
  Sparkles,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  Eye,
  RefreshCw,
  Trash2,
  Search,
} from 'lucide-react'

type TechPackStatus = 'pending' | 'processing' | 'completed' | 'failed'

interface TechPack {
  id: string
  styleRef: string
  productName?: string
  season?: string
  designer?: string
  status: TechPackStatus
  fileName?: string
  createdAt: string
  processedAt?: string
}

const statusConfig: Record<TechPackStatus, { label: string; icon: typeof CheckCircle2; className: string }> = {
  pending: {
    label: 'Pending',
    icon: Clock,
    className: 'bg-gray-100 text-gray-700',
  },
  processing: {
    label: 'Processing',
    icon: Loader2,
    className: 'bg-blue-100 text-blue-700',
  },
  completed: {
    label: 'Completed',
    icon: CheckCircle2,
    className: 'bg-green-100 text-green-700',
  },
  failed: {
    label: 'Failed',
    icon: AlertCircle,
    className: 'bg-red-100 text-red-700',
  },
}

function StatusBadge({ status }: { status: TechPackStatus }) {
  const config = statusConfig[status] || statusConfig.pending
  const Icon = config.icon

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.className}`}>
      <Icon className={`h-3.5 w-3.5 ${status === 'processing' ? 'animate-spin' : ''}`} />
      {config.label}
    </span>
  )
}

export default function TechPacksPage() {
  const params = useParams()
  const router = useRouter()
  const tenantSlug = params.tenantSlug as string
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const canManage = user?.roles?.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role)) ?? false

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['tech-packs', statusFilter, searchQuery],
    queryFn: () =>
      apiClient.getTechPacks({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        search: searchQuery || undefined,
      }),
    refetchInterval: 5000, // Poll every 5s to see processing updates
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteTechPack(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tech-packs'] })
    },
  })

  const reprocessMutation = useMutation({
    mutationFn: (id: string) => apiClient.reprocessTechPack(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tech-packs'] })
    },
  })

  const techPacks: TechPack[] = data?.items || []
  const total = data?.total || 0

  const summary = {
    total,
    completed: techPacks.filter((tp) => tp.status === 'completed').length,
    processing: techPacks.filter((tp) => tp.status === 'processing').length,
    failed: techPacks.filter((tp) => tp.status === 'failed').length,
  }

  const handleViewDetails = (id: string) => {
    router.push(`/c/${tenantSlug}/tech-packs/${id}`)
  }

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this Tech Pack?')) {
      deleteMutation.mutate(id)
    }
  }

  const handleReprocess = (id: string) => {
    reprocessMutation.mutate(id)
  }

  const pageActions = canManage ? (
    <Button
      onClick={() => setIsUploadModalOpen(true)}
      className="relative group bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white px-5 py-2.5 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
    >
      <div className="absolute inset-0 bg-gradient-to-r from-violet-400 to-purple-400 rounded-lg blur-lg opacity-25 group-hover:opacity-40 transition-opacity"></div>
      <div className="relative flex items-center gap-2">
        <Upload className="h-4 w-4" />
        <span className="font-semibold">Upload Tech Pack</span>
        <Sparkles className="h-4 w-4 text-yellow-300 animate-pulse" />
      </div>
    </Button>
  ) : undefined

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Tech Packs"
          description="Manage and extract data from your tech pack documents."
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
        title="Tech Packs"
        description="Manage and extract data from your tech pack documents."
        actions={pageActions}
      />

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Total Tech Packs</CardDescription>
            <CardTitle>{summary.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Completed</CardDescription>
            <CardTitle className="text-green-600">{summary.completed}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Processing</CardDescription>
            <CardTitle className="text-blue-600">{summary.processing}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Failed</CardDescription>
            <CardTitle className="text-red-600">{summary.failed}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search by style ref or product name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white"
        >
          <option value="all">All statuses</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Table */}
      {techPacks.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-5 w-5" />}
          title="No tech packs found"
          description={
            searchQuery || statusFilter !== 'all'
              ? 'Try adjusting your filters to find what you are looking for.'
              : 'Upload your first tech pack to extract product specifications automatically.'
          }
          action={
            canManage
              ? {
                  label: 'Upload Tech Pack',
                  onClick: () => setIsUploadModalOpen(true),
                }
              : undefined
          }
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Style Ref</TableHead>
              <TableHead>Product Name</TableHead>
              <TableHead>Season</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>File</TableHead>
              <TableHead>Uploaded</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {techPacks.map((techPack) => (
              <TableRow key={techPack.id}>
                <TableCell className="font-medium">{techPack.styleRef}</TableCell>
                <TableCell>{techPack.productName || '-'}</TableCell>
                <TableCell>{techPack.season || '-'}</TableCell>
                <TableCell>
                  <StatusBadge status={techPack.status} />
                </TableCell>
                <TableCell className="text-sm text-neutral-500">
                  {techPack.fileName || '-'}
                </TableCell>
                <TableCell className="text-sm text-neutral-500">
                  {formatRelativeTime(techPack.createdAt)}
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => handleViewDetails(techPack.id)}
                      title="View details"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    {techPack.status === 'failed' && canManage && (
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => handleReprocess(techPack.id)}
                        loading={reprocessMutation.isPending}
                        title="Reprocess"
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                    )}
                    {canManage && (
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={() => handleDelete(techPack.id)}
                        loading={deleteMutation.isPending}
                        title="Delete"
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Upload Modal */}
      <TechPackUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={() => {
          setIsUploadModalOpen(false)
          refetch()
        }}
      />
    </div>
  )
}
