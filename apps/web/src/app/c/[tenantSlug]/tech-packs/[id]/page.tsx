'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { useAuth } from '@/components/providers/auth-provider'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { CreateLotFromTechPackModal } from '@/components/tech-packs/create-lot-from-tech-pack-modal'
import { UserRole } from '@qa-dashboard/shared'
import { formatDate } from '@/lib/utils'
import {
  ArrowLeft,
  RefreshCw,
  Trash2,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  FileText,
  Palette,
  Ruler,
  Scissors,
  Tag,
  Package,
  Shirt,
  ListChecks,
  Sparkles,
  Plus,
  Image,
  ChevronLeft,
  ChevronRight,
  X,
  FolderOpen,
} from 'lucide-react'

type TechPackStatus = 'pending' | 'processing' | 'completed' | 'failed'

interface TechPackImage {
  url: string
  key: string
  pageNumber?: number
  width?: number
  height?: number
  description?: string
  type?: string
}

interface TechPack {
  id: string
  tenantId: string
  styleRef: string
  productName?: string
  season?: string
  designer?: string
  sampleSize?: string
  sizeRange?: string[]
  status: TechPackStatus
  fileKey?: string
  fileName?: string
  fileSize?: number
  materialComposition?: any[]
  colorways?: any[]
  sizeSpecifications?: any[]
  measurementTolerances?: Record<string, number>
  grading?: any
  constructionDetails?: any[]
  artwork?: any[]
  fabricMap?: any[]
  labels?: any[]
  hangTags?: any[]
  packaging?: any[]
  foldingInstructions?: any[]
  careInstructions?: any[]
  billOfMaterials?: any[]
  images?: TechPackImage[]
  rawExtractedData?: any
  processingError?: string
  createdAt: string
  updatedAt: string
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
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${config.className}`}>
      <Icon className={`h-4 w-4 ${status === 'processing' ? 'animate-spin' : ''}`} />
      {config.label}
    </span>
  )
}

function DataSection({ title, icon: Icon, children, isEmpty }: {
  title: string
  icon: typeof FileText
  children: React.ReactNode
  isEmpty?: boolean
}) {
  if (isEmpty) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="h-5 w-5 text-violet-600" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

// Helper to get relevant page images based on imageDescriptions
function getRelevantPageImages(
  images: TechPackImage[] | undefined,
  imageDescriptions: any[] | undefined,
  contentTypes: string[]
): TechPackImage[] {
  if (!images || images.length === 0) return []
  if (!imageDescriptions || imageDescriptions.length === 0) return []

  // Find page numbers that match the content types
  const relevantPageNumbers = imageDescriptions
    .filter((desc: any) => contentTypes.some(type =>
      desc.type?.toLowerCase().includes(type.toLowerCase())
    ))
    .map((desc: any) => desc.pageNumber)

  // Filter images to only those pages
  return images.filter(img => relevantPageNumbers.includes(img.pageNumber))
}

// Component to show relevant page images for a section
function RelevantPageImages({ images }: { images: TechPackImage[] }) {
  if (!images || images.length === 0) return null

  return (
    <div className="mb-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
      <p className="text-sm text-slate-600 mb-3">Reference from tech pack:</p>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {images.map((image, idx) => (
          <a
            key={idx}
            href={image.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0"
          >
            <img
              src={image.url}
              alt={`Page ${image.pageNumber || idx + 1}`}
              className="h-32 w-auto rounded border border-slate-200 hover:border-violet-400 transition-colors"
            />
          </a>
        ))}
      </div>
    </div>
  )
}

function ColorwaysList({ colorways }: { colorways: any[] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {colorways.map((cw, idx) => (
        <div
          key={idx}
          className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-100"
        >
          {cw.hex && (
            <div
              className="w-8 h-8 rounded-lg border border-slate-200 flex-shrink-0"
              style={{ backgroundColor: cw.hex }}
            />
          )}
          <div className="min-w-0">
            <p className="font-medium text-sm truncate">{cw.name || cw.colorName || `Color ${idx + 1}`}</p>
            {cw.code && <p className="text-xs text-slate-500">{cw.code}</p>}
          </div>
        </div>
      ))}
    </div>
  )
}

function MeasurementsTable({ specs }: { specs: any[] }) {
  if (!specs || specs.length === 0) return <p className="text-slate-500 text-sm">No size specifications available</p>

  // Check if specs are in the new format { size, measurements: {...} }
  const isNewFormat = specs[0]?.measurements && typeof specs[0].measurements === 'object'

  if (isNewFormat) {
    // New format: { size: "M", measurements: { hem: 14.5, waist: 10 } }
    // Transform to table with sizes as columns and measurements as rows
    const sizes = specs.map(s => s.size).filter(Boolean)
    const allMeasurements = new Set<string>()
    specs.forEach(spec => {
      if (spec.measurements) {
        Object.keys(spec.measurements).forEach(m => allMeasurements.add(m))
      }
    })
    const measurementNames = Array.from(allMeasurements)

    // Create a lookup map for quick access
    const sizeToMeasurements: Record<string, Record<string, number>> = {}
    specs.forEach(spec => {
      if (spec.size && spec.measurements) {
        sizeToMeasurements[spec.size] = spec.measurements
      }
    })

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 px-3 font-medium text-slate-700">Measurement</th>
              {sizes.map(size => (
                <th key={size} className="text-center py-2 px-3 font-medium text-slate-700">{size}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {measurementNames.map((measurement, idx) => (
              <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-2 px-3 font-medium capitalize">{measurement.replace(/([A-Z])/g, ' $1').trim()}</td>
                {sizes.map(size => (
                  <td key={size} className="text-center py-2 px-3">
                    {sizeToMeasurements[size]?.[measurement] ?? '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  // Old format: { pointOfMeasure: "hem", S: 13, M: 14.5, L: 16 }
  const sizes = Object.keys(specs[0] || {}).filter(key => !['pointOfMeasure', 'pom', 'tolerance', 'unit'].includes(key.toLowerCase()))

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-2 px-3 font-medium text-slate-700">Point of Measure</th>
            {sizes.map(size => (
              <th key={size} className="text-center py-2 px-3 font-medium text-slate-700">{size}</th>
            ))}
            <th className="text-center py-2 px-3 font-medium text-slate-700">Tolerance</th>
          </tr>
        </thead>
        <tbody>
          {specs.map((spec, idx) => (
            <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-2 px-3 font-medium">{spec.pointOfMeasure || spec.pom || `Measure ${idx + 1}`}</td>
              {sizes.map(size => (
                <td key={size} className="text-center py-2 px-3">{spec[size] || '-'}</td>
              ))}
              <td className="text-center py-2 px-3 text-slate-500">{spec.tolerance || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MaterialsList({ materials }: { materials: any[] }) {
  return (
    <div className="space-y-2">
      {materials.map((mat, idx) => (
        <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
          <span className="font-medium">{mat.fiber || mat.material || mat.name || `Material ${idx + 1}`}</span>
          <span className="text-slate-600">{mat.percentage || mat.percent}%</span>
        </div>
      ))}
    </div>
  )
}

function ConstructionList({ details, relevantImages }: { details: any[], relevantImages?: TechPackImage[] }) {
  // Check if details have rich structure
  const hasRichData = details.some(d => typeof d === 'object' && (d.area || d.stitchType || d.stitchCode))

  if (!hasRichData) {
    // Simple list for basic string details
    return (
      <div className="space-y-4">
        <RelevantPageImages images={relevantImages || []} />
        <ul className="space-y-2">
          {details.map((detail, idx) => (
            <li key={idx} className="flex items-start gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-violet-500 mt-2 flex-shrink-0" />
              <span className="text-slate-700">{typeof detail === 'string' ? detail : detail.description || detail.detail || JSON.stringify(detail)}</span>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  // Rich table display for structured construction details
  return (
    <div className="space-y-4">
      <RelevantPageImages images={relevantImages || []} />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left p-3 font-medium text-slate-600">Code</th>
              <th className="text-left p-3 font-medium text-slate-600">Area</th>
              <th className="text-left p-3 font-medium text-slate-600">Stitch Type</th>
              <th className="text-left p-3 font-medium text-slate-600">Description</th>
              <th className="text-left p-3 font-medium text-slate-600">Notes</th>
            </tr>
          </thead>
          <tbody>
            {details.map((detail, idx) => (
              <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-3">
                  {detail.stitchCode && (
                    <span className="inline-flex items-center justify-center w-8 h-8 bg-violet-100 text-violet-700 rounded-full font-bold">
                      {detail.stitchCode}
                    </span>
                  )}
                </td>
                <td className="p-3">
                  <div className="font-medium text-slate-900">{detail.area}</div>
                </td>
                <td className="p-3">
                  <div className="text-slate-700">{detail.stitchType}</div>
                </td>
                <td className="p-3">
                  <div className="text-slate-700">{detail.description}</div>
                </td>
                <td className="p-3">
                  <div className="text-slate-500 text-xs">{detail.notes !== 'N/A' ? detail.notes : '-'}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function FoldingInstructionsGallery({ instructions, relevantImages }: { instructions: any[], relevantImages?: TechPackImage[] }) {
  return (
    <div className="space-y-4">
      <RelevantPageImages images={relevantImages || []} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {instructions.map((step, idx) => (
          <div key={idx} className="border border-slate-200 rounded-lg overflow-hidden bg-white">
            {step.imageUrl && (
              <a href={step.imageUrl} target="_blank" rel="noopener noreferrer" className="block">
                <div className="aspect-video bg-slate-100 relative group">
                  <img
                    src={step.imageUrl}
                    alt={`Passo ${step.step}`}
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                </div>
              </a>
            )}
            <div className="p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-6 h-6 bg-violet-100 text-violet-700 rounded-full flex items-center justify-center text-sm font-medium">
                  {step.step || idx + 1}
                </span>
                <span className="text-sm font-medium text-slate-700">Step {step.step || idx + 1}</span>
              </div>
              <p className="text-sm text-slate-700">{step.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function LabelsGallery({ labels, relevantImages }: { labels: any[], relevantImages?: TechPackImage[] }) {
  return (
    <div className="space-y-4">
      <RelevantPageImages images={relevantImages || []} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {labels.map((label, idx) => (
          <div key={idx} className="border border-slate-200 rounded-lg overflow-hidden bg-white">
            {label.imageUrl && (
              <a href={label.imageUrl} target="_blank" rel="noopener noreferrer" className="block">
                <div className="aspect-video bg-slate-100 relative group">
                  <img
                    src={label.imageUrl}
                    alt={label.type || `Label ${idx + 1}`}
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                </div>
              </a>
            )}
            <div className="p-3">
              <p className="font-medium text-slate-900">{label.type || `Label ${idx + 1}`}</p>
              <div className="mt-1 text-sm text-slate-600 space-y-0.5">
                {(label.width || label.height) && (
                  <p>Size: {label.width} × {label.height}</p>
                )}
                {label.material && (
                  <p>Material: {label.material}</p>
                )}
                {label.placement && (
                  <p>Placement: {label.placement}</p>
                )}
                {label.content && <p className="text-xs mt-1 italic">{label.content}</p>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function HangTagsGallery({ hangTags, relevantImages }: { hangTags: any[], relevantImages?: TechPackImage[] }) {
  return (
    <div className="space-y-4">
      <RelevantPageImages images={relevantImages || []} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {hangTags.map((tag, idx) => (
          <div key={idx} className="border border-slate-200 rounded-lg overflow-hidden bg-white">
            <div className="grid grid-cols-2 gap-2 p-2 bg-slate-50">
              {tag.frontImageUrl && (
                <a href={tag.frontImageUrl} target="_blank" rel="noopener noreferrer" className="block">
                  <div className="aspect-[3/4] bg-white rounded border border-slate-200 relative group">
                    <img
                      src={tag.frontImageUrl}
                      alt="Front"
                      className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                    />
                    <span className="absolute bottom-1 left-1 text-xs bg-black/60 text-white px-1.5 py-0.5 rounded">Front</span>
                  </div>
                </a>
              )}
              {tag.backImageUrl && (
                <a href={tag.backImageUrl} target="_blank" rel="noopener noreferrer" className="block">
                  <div className="aspect-[3/4] bg-white rounded border border-slate-200 relative group">
                    <img
                      src={tag.backImageUrl}
                      alt="Back"
                      className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                    />
                    <span className="absolute bottom-1 left-1 text-xs bg-black/60 text-white px-1.5 py-0.5 rounded">Back</span>
                  </div>
                </a>
              )}
              {tag.imageUrl && !tag.frontImageUrl && !tag.backImageUrl && (
                <a href={tag.imageUrl} target="_blank" rel="noopener noreferrer" className="block col-span-2">
                  <div className="aspect-video bg-white rounded border border-slate-200 relative group">
                    <img
                      src={tag.imageUrl}
                      alt={`Hang Tag ${idx + 1}`}
                      className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                    />
                  </div>
                </a>
              )}
            </div>
            <div className="p-3">
              <p className="font-medium text-slate-900">Hang Tag {idx + 1}</p>
              <div className="mt-1 text-sm text-slate-600 space-y-0.5">
                {(tag.width || tag.height) && (
                  <p>{tag.width} × {tag.height}</p>
                )}
                {tag.material && <p>Material: {tag.material}</p>}
                {tag.attachment && <p>Attachment: {tag.attachment}</p>}
                {tag.content && <p className="text-xs mt-1 italic">{tag.content}</p>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function PackagingGallery({ packaging, relevantImages }: { packaging: any[], relevantImages?: TechPackImage[] }) {
  return (
    <div className="space-y-4">
      <RelevantPageImages images={relevantImages || []} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {packaging.map((pkg, idx) => (
          <div key={idx} className="border border-slate-200 rounded-lg overflow-hidden bg-white">
            {(pkg.imageUrl || pkg.frontImageUrl) && (
              <a href={pkg.imageUrl || pkg.frontImageUrl} target="_blank" rel="noopener noreferrer" className="block">
                <div className="aspect-video bg-slate-100 relative group">
                  <img
                    src={pkg.imageUrl || pkg.frontImageUrl}
                    alt={pkg.type || `Packaging ${idx + 1}`}
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                </div>
              </a>
            )}
            <div className="p-3">
              <p className="font-medium text-slate-900">{pkg.type || `Packaging ${idx + 1}`}</p>
              <div className="mt-1 text-sm text-slate-600 space-y-0.5">
                {(pkg.width || pkg.height) && (
                  <p>{pkg.width} × {pkg.height}</p>
                )}
                {pkg.material && <p>Material: {pkg.material}</p>}
                {pkg.notes && <p className="text-xs mt-1 italic">{pkg.notes}</p>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ArtworkGallery({ artwork, relevantImages }: { artwork: any[], relevantImages?: TechPackImage[] }) {
  return (
    <div className="space-y-4">
      <RelevantPageImages images={relevantImages || []} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {artwork.map((art, idx) => (
          <div key={idx} className="border border-slate-200 rounded-lg overflow-hidden bg-white">
            {art.imageUrl && (
              <a href={art.imageUrl} target="_blank" rel="noopener noreferrer" className="block">
                <div className="aspect-square bg-slate-100 relative group">
                  <img
                    src={art.imageUrl}
                    alt={art.type || `Artwork ${idx + 1}`}
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                </div>
              </a>
            )}
            <div className="p-3">
              <p className="font-medium text-slate-900">{art.type || `Artwork ${idx + 1}`}</p>
              <div className="mt-1 text-sm text-slate-600 space-y-0.5">
                {art.placement && <p>Placement: {art.placement}</p>}
                {art.technique && <p>Technique: {art.technique}</p>}
                {(art.width || art.height) && (
                  <p>Size: {art.width} × {art.height}</p>
                )}
                {art.colors?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {art.colors.map((color: string, cidx: number) => (
                      <span key={cidx} className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{color}</span>
                    ))}
                  </div>
                )}
                {art.notes && <p className="text-xs mt-1 italic">{art.notes}</p>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CareInstructionsList({ instructions }: { instructions: any[] }) {
  const formatInstructions = (inst: any): string => {
    if (typeof inst === 'string') return inst
    if (inst.text) return inst.text
    if (inst.instructions) {
      // instructions can be a string or array of strings
      if (Array.isArray(inst.instructions)) {
        return inst.instructions.join(', ')
      }
      return String(inst.instructions)
    }
    return JSON.stringify(inst)
  }

  return (
    <div className="space-y-3">
      {instructions.map((inst, idx) => (
        <div key={idx} className="p-3 bg-slate-50 rounded-lg">
          {inst.language && <p className="text-xs font-medium text-violet-600 mb-1">{inst.language}</p>}
          <p className="text-slate-700">{formatInstructions(inst)}</p>
        </div>
      ))}
    </div>
  )
}

function BOMTable({ bom }: { bom: any[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-2 px-3 font-medium text-slate-700">Item</th>
            <th className="text-left py-2 px-3 font-medium text-slate-700">Description</th>
            <th className="text-left py-2 px-3 font-medium text-slate-700">Supplier</th>
            <th className="text-center py-2 px-3 font-medium text-slate-700">Qty</th>
          </tr>
        </thead>
        <tbody>
          {bom.map((item, idx) => (
            <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-2 px-3 font-medium">{item.item || item.name || `Item ${idx + 1}`}</td>
              <td className="py-2 px-3">{item.description || '-'}</td>
              <td className="py-2 px-3">{item.supplier || '-'}</td>
              <td className="text-center py-2 px-3">{item.quantity || item.qty || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function TechPackDetailPage() {
  const params = useParams()
  const router = useRouter()
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const tenantSlug = params.tenantSlug as string
  const techPackId = params.id as string

  const [isCreateLotModalOpen, setIsCreateLotModalOpen] = useState(false)

  const canManage = user?.roles?.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role)) ?? false

  const { data: techPack, isLoading, error } = useQuery<TechPack>({
    queryKey: ['tech-pack', techPackId],
    queryFn: () => apiClient.getTechPack(techPackId),
    refetchInterval: (data) => {
      // Poll while processing
      if (data?.state?.data?.status === 'processing') return 3000
      return false
    },
  })

  const { data: linkedLots = [] } = useQuery({
    queryKey: ['tech-pack-lots', techPackId],
    queryFn: () => apiClient.getTechPackLots(techPackId),
    enabled: !!techPack,
  })

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.deleteTechPack(techPackId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tech-packs'] })
      router.push(`/c/${tenantSlug}/tech-packs`)
    },
  })

  const reprocessMutation = useMutation({
    mutationFn: () => apiClient.reprocessTechPack(techPackId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tech-pack', techPackId] })
    },
  })

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this Tech Pack?')) {
      deleteMutation.mutate()
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader title="Tech Pack Details" />
        <Card>
          <CardContent className="flex h-48 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !techPack) {
    return (
      <div className="space-y-8">
        <PageHeader title="Tech Pack Not Found" />
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <p className="text-slate-600">This tech pack could not be found or you do not have access to it.</p>
            <Button
              variant="secondary"
              className="mt-4"
              onClick={() => router.push(`/c/${tenantSlug}/tech-packs`)}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Tech Packs
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title={techPack.styleRef}
        description={techPack.productName || 'Tech Pack Details'}
        meta={
          <div className="flex items-center gap-3">
            <StatusBadge status={techPack.status} />
            {techPack.processedAt && (
              <span className="text-xs text-slate-500">
                Processed {formatDate(techPack.processedAt)}
              </span>
            )}
          </div>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={() => router.push(`/c/${tenantSlug}/tech-packs`)}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            {techPack.status === 'completed' && canManage && (
              <Button
                onClick={() => setIsCreateLotModalOpen(true)}
                className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Lot
              </Button>
            )}
            {techPack.status === 'failed' && canManage && (
              <Button
                variant="secondary"
                onClick={() => reprocessMutation.mutate()}
                loading={reprocessMutation.isPending}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Reprocess
              </Button>
            )}
            {canManage && (
              <Button
                variant="danger"
                onClick={handleDelete}
                loading={deleteMutation.isPending}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
            )}
          </div>
        }
      />

      {/* Processing Message */}
      {techPack.status === 'processing' && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="py-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-full">
                <Sparkles className="h-6 w-6 text-blue-600 animate-pulse" />
              </div>
              <div>
                <p className="font-medium text-blue-900">AI is extracting data from your tech pack...</p>
                <p className="text-sm text-blue-700">This usually takes 30-60 seconds. The page will update automatically.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Message */}
      {techPack.status === 'failed' && techPack.processingError && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-red-100 rounded-full">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <p className="font-medium text-red-900">Processing failed</p>
                <p className="text-sm text-red-700">{techPack.processingError}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Basic Info */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Style Reference</CardDescription>
            <CardTitle>{techPack.styleRef}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Season</CardDescription>
            <CardTitle>{techPack.season || '-'}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Designer</CardDescription>
            <CardTitle>{techPack.designer || '-'}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Sample Size</CardDescription>
            <CardTitle>{techPack.sampleSize || '-'}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Extracted Data Sections */}
      {techPack.status === 'completed' && (
        <div className="grid gap-6">
          {/* Colorways */}
          <DataSection
            title="Colorways"
            icon={Palette}
            isEmpty={!techPack.colorways?.length}
          >
            <ColorwaysList colorways={techPack.colorways || []} />
          </DataSection>

          {/* Size Specifications */}
          <DataSection
            title="Size Specifications"
            icon={Ruler}
            isEmpty={!techPack.sizeSpecifications?.length}
          >
            <MeasurementsTable specs={techPack.sizeSpecifications || []} />
          </DataSection>

          {/* Material Composition */}
          <DataSection
            title="Material Composition"
            icon={Shirt}
            isEmpty={!techPack.materialComposition?.length}
          >
            <MaterialsList materials={techPack.materialComposition || []} />
          </DataSection>

          {/* Construction Details */}
          <DataSection
            title="Construction Details"
            icon={Scissors}
            isEmpty={!techPack.constructionDetails?.length}
          >
            <ConstructionList
              details={techPack.constructionDetails || []}
              relevantImages={getRelevantPageImages(techPack.images, techPack.rawExtractedData?.imageDescriptions, ['construction', 'stitch', 'seam', 'specs'])}
            />
          </DataSection>

          {/* Care Instructions */}
          <DataSection
            title="Care Instructions"
            icon={Tag}
            isEmpty={!techPack.careInstructions?.length}
          >
            <CareInstructionsList instructions={techPack.careInstructions || []} />
          </DataSection>

          {/* Bill of Materials */}
          <DataSection
            title="Bill of Materials"
            icon={ListChecks}
            isEmpty={!techPack.billOfMaterials?.length}
          >
            <BOMTable bom={techPack.billOfMaterials || []} />
          </DataSection>

          {/* Artwork */}
          <DataSection
            title="Artwork & Graphics"
            icon={Palette}
            isEmpty={!techPack.artwork?.length}
          >
            <ArtworkGallery
              artwork={techPack.artwork || []}
              relevantImages={getRelevantPageImages(techPack.images, techPack.rawExtractedData?.imageDescriptions, ['artwork', 'graphic', 'print', 'embroid'])}
            />
          </DataSection>

          {/* Labels */}
          <DataSection
            title="Labels"
            icon={Tag}
            isEmpty={!techPack.labels?.length}
          >
            <LabelsGallery
              labels={techPack.labels || []}
              relevantImages={getRelevantPageImages(techPack.images, techPack.rawExtractedData?.imageDescriptions, ['label'])}
            />
          </DataSection>

          {/* Hang Tags */}
          <DataSection
            title="Hang Tags"
            icon={Tag}
            isEmpty={!techPack.hangTags?.length}
          >
            <HangTagsGallery
              hangTags={techPack.hangTags || []}
              relevantImages={getRelevantPageImages(techPack.images, techPack.rawExtractedData?.imageDescriptions, ['hangtag', 'hang tag', 'tag'])}
            />
          </DataSection>

          {/* Packaging */}
          <DataSection
            title="Packaging"
            icon={Package}
            isEmpty={!techPack.packaging?.length}
          >
            <PackagingGallery
              packaging={techPack.packaging || []}
              relevantImages={getRelevantPageImages(techPack.images, techPack.rawExtractedData?.imageDescriptions, ['packaging', 'polybag', 'box'])}
            />
          </DataSection>

          {/* Folding Instructions */}
          <DataSection
            title="Folding Instructions"
            icon={FolderOpen}
            isEmpty={!techPack.foldingInstructions?.length}
          >
            <FoldingInstructionsGallery
              instructions={techPack.foldingInstructions || []}
              relevantImages={getRelevantPageImages(techPack.images, techPack.rawExtractedData?.imageDescriptions, ['folding', 'fold'])}
            />
          </DataSection>

          {/* Linked Lots */}
          {linkedLots.length > 0 && (
            <DataSection title="Linked Lots" icon={Package} isEmpty={false}>
              <div className="space-y-2">
                {linkedLots.map((lot: any) => (
                  <div
                    key={lot.id}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 cursor-pointer"
                    onClick={() => router.push(`/c/${tenantSlug}/lots/${lot.id}`)}
                  >
                    <div>
                      <p className="font-medium">{lot.styleRef}</p>
                      <p className="text-sm text-slate-500">{lot.quantityTotal} units</p>
                    </div>
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      lot.status === 'approved' ? 'bg-green-100 text-green-700' :
                      lot.status === 'inspection' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {lot.status}
                    </span>
                  </div>
                ))}
              </div>
            </DataSection>
          )}
        </div>
      )}

      {/* File Info */}
      {techPack.fileName && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-5 w-5 text-slate-400" />
              Source File
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="p-3 bg-slate-100 rounded-lg">
                <FileText className="h-6 w-6 text-slate-600" />
              </div>
              <div>
                <p className="font-medium">{techPack.fileName}</p>
                {techPack.fileSize && (
                  <p className="text-sm text-slate-500">
                    {(techPack.fileSize / 1024 / 1024).toFixed(2)} MB
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tech Pack Page Images Gallery - at the bottom */}
      {techPack.status === 'completed' && techPack.images && techPack.images.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Image className="h-5 w-5 text-violet-600" />
              Tech Pack Pages ({techPack.images.length})
            </CardTitle>
            <CardDescription>
              All pages extracted from the original tech pack document
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {techPack.images.map((image, idx) => (
                <a
                  key={idx}
                  href={image.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group relative aspect-[3/4] bg-slate-100 rounded-lg overflow-hidden border border-slate-200 hover:border-violet-400 hover:shadow-lg transition-all"
                >
                  <img
                    src={image.url}
                    alt={`Page ${image.pageNumber || idx + 1}`}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="absolute bottom-0 left-0 right-0 p-2 text-white text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                    Page {image.pageNumber || idx + 1}
                  </div>
                </a>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create Lot Modal */}
      {techPack && (
        <CreateLotFromTechPackModal
          isOpen={isCreateLotModalOpen}
          onClose={() => setIsCreateLotModalOpen(false)}
          techPack={techPack}
          tenantSlug={tenantSlug}
        />
      )}
    </div>
  )
}
