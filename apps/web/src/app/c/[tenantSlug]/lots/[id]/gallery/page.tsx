'use client'

import { useCallback, useEffect, useState, useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import Link from 'next/link'
import { ImageZoomViewer } from '@/components/ui/image-zoom-viewer'
import {
  ArrowLeftIcon,
  CheckCircle2Icon,
  XCircleIcon,
  AlertCircleIcon,
  ImageIcon,
  ZoomInIcon,
  XIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  PackageIcon,
  CameraIcon,
  RulerIcon,
  AlertTriangleIcon
} from 'lucide-react'

interface PieceGroup {
  pieceId: string
  pieceNumber: number
  status: string
  photos: any[]
  measurements?: any
  defectCount: number
  firstPhotoTime: string
  lastPhotoTime: string
}

export default function LotGalleryPage() {
  const params = useParams()
  const router = useRouter()
  const lotId = params?.id as string
  const tenantSlug = params?.tenantSlug as string

  const [gallery, setGallery] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedPhoto, setSelectedPhoto] = useState<any>(null)
  const [currentPhotoIndex, setCurrentPhotoIndex] = useState(0)
  const [expandedPieces, setExpandedPieces] = useState<Set<string>>(new Set())
  const [selectedPiece, setSelectedPiece] = useState<string | null>(null)

  const loadGallery = useCallback(async () => {
    if (!lotId) return

    try {
      setLoading(true)
      const data = await apiClient.getLotGallery(lotId, statusFilter || undefined)
      setGallery(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load gallery')
    } finally {
      setLoading(false)
    }
  }, [lotId, statusFilter])

  useEffect(() => {
    loadGallery()
  }, [loadGallery])

  // Group photos by piece
  const pieceGroups = useMemo(() => {
    if (!gallery?.photos) return []

    const groups = new Map<string, PieceGroup>()

    gallery.photos.forEach((photo: any) => {
      const pieceKey = `piece-${photo.pieceNumber}`

      if (!groups.has(pieceKey)) {
        groups.set(pieceKey, {
          pieceId: photo.pieceId,
          pieceNumber: photo.pieceNumber,
          status: photo.pieceStatus,
          photos: [],
          measurements: photo.measurements,
          defectCount: 0,
          firstPhotoTime: photo.capturedAt,
          lastPhotoTime: photo.capturedAt
        })
      }

      const group = groups.get(pieceKey)!
      group.photos.push(photo)

      // Update times
      if (new Date(photo.capturedAt) < new Date(group.firstPhotoTime)) {
        group.firstPhotoTime = photo.capturedAt
      }
      if (new Date(photo.capturedAt) > new Date(group.lastPhotoTime)) {
        group.lastPhotoTime = photo.capturedAt
      }

      // Count defects
      if (photo.pieceStatus === 'defect' || photo.pieceStatus === 'potential_defect') {
        group.defectCount++
      }
    })

    // Sort by piece number
    return Array.from(groups.values()).sort((a, b) => a.pieceNumber - b.pieceNumber)
  }, [gallery])

  // Calculate statistics
  const stats = useMemo(() => {
    if (!pieceGroups) return { totalPieces: 0, totalPhotos: 0, ok: 0, defects: 0, potential: 0, pending: 0 }

    const totalPieces = pieceGroups.length
    const totalPhotos = pieceGroups.reduce((sum, group) => sum + group.photos.length, 0)
    const ok = pieceGroups.filter(g => g.status === 'ok').length
    const defects = pieceGroups.filter(g => g.status === 'defect').length
    const potential = pieceGroups.filter(g => g.status === 'potential_defect').length
    const pending = pieceGroups.filter(g => g.status === 'pending_review').length

    return { totalPieces, totalPhotos, ok, defects, potential, pending }
  }, [pieceGroups])

  const togglePieceExpansion = (pieceId: string) => {
    const newExpanded = new Set(expandedPieces)
    if (newExpanded.has(pieceId)) {
      newExpanded.delete(pieceId)
    } else {
      newExpanded.add(pieceId)
    }
    setExpandedPieces(newExpanded)
  }

  const handlePhotoClick = (photo: any, piece: PieceGroup) => {
    setSelectedPhoto(photo)
    setSelectedPiece(`piece-${piece.pieceNumber}`)
    const photoIndex = piece.photos.findIndex(p => p.id === photo.id)
    setCurrentPhotoIndex(photoIndex)
  }

  const navigatePhoto = useCallback((direction: 'prev' | 'next') => {
    if (!selectedPiece || !gallery?.photos) return

    const piece = pieceGroups.find(g => `piece-${g.pieceNumber}` === selectedPiece)
    if (!piece) return

    const newIndex = direction === 'prev'
      ? (currentPhotoIndex - 1 + piece.photos.length) % piece.photos.length
      : (currentPhotoIndex + 1) % piece.photos.length

    setCurrentPhotoIndex(newIndex)
    setSelectedPhoto(piece.photos[newIndex])
  }, [pieceGroups, selectedPiece, currentPhotoIndex, gallery])

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!selectedPhoto) return

      if (e.key === 'ArrowLeft') {
        navigatePhoto('prev')
      } else if (e.key === 'ArrowRight') {
        navigatePhoto('next')
      } else if (e.key === 'Escape') {
        setSelectedPhoto(null)
        setSelectedPiece(null)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedPhoto, navigatePhoto])

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'ok': return 'bg-green-500 text-white'
      case 'defect': return 'bg-red-500 text-white'
      case 'potential_defect': return 'bg-amber-500 text-white'
      default: return 'bg-blue-500 text-white'
    }
  }

  const getStatusIcon = (status: string) => {
    switch(status) {
      case 'ok': return <CheckCircle2Icon className="h-4 w-4" />
      case 'defect': return <XCircleIcon className="h-4 w-4" />
      case 'potential_defect': return <AlertTriangleIcon className="h-4 w-4" />
      default: return <AlertCircleIcon className="h-4 w-4" />
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-neutral-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error || !gallery) {
    return (
      <div className="min-h-screen bg-neutral-50 px-4 py-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center">
            <XCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-800 text-lg font-semibold mb-2">{error || 'Gallery not found'}</p>
            <Link
              href={`/c/${tenantSlug}/lots/${lotId}`}
              className="mt-4 inline-flex items-center gap-2 text-primary-600 hover:text-primary-800 font-medium"
            >
              <ArrowLeftIcon className="h-4 w-4" />
              Back to Lot
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 to-neutral-100">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center gap-2 text-sm text-neutral-600 mb-6">
          <Link href={`/c/${tenantSlug}/lots`} className="hover:text-neutral-900 transition">
            Lots
          </Link>
          <span>/</span>
          <Link href={`/c/${tenantSlug}/lots/${lotId}`} className="hover:text-neutral-900 transition">
            Lot Details
          </Link>
          <span>/</span>
          <span className="text-neutral-900 font-medium">Gallery</span>
        </div>

        {/* Header with Stats */}
        <div className="mb-8">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-4xl font-bold text-neutral-900 mb-2 flex items-center gap-3">
                <PackageIcon className="h-10 w-10 text-primary-600" />
                Piece Gallery
              </h1>
              <p className="text-neutral-600 text-lg">
                {stats.totalPieces} pieces with {stats.totalPhotos} photos
              </p>
            </div>
            <Link
              href={`/c/${tenantSlug}/lots/${lotId}`}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-white border border-neutral-300 rounded-xl hover:bg-neutral-50 font-medium transition shadow-sm"
            >
              <ArrowLeftIcon className="h-4 w-4" />
              Back to Lot
            </Link>
          </div>

          {/* Statistics Cards */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-neutral-200 p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary-50">
                  <PackageIcon className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-neutral-900">{stats.totalPieces}</div>
                  <div className="text-xs text-neutral-500 uppercase tracking-wide">Pieces</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-neutral-200 p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-50">
                  <CameraIcon className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-neutral-900">{stats.totalPhotos}</div>
                  <div className="text-xs text-neutral-500 uppercase tracking-wide">Photos</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-neutral-200 p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-50">
                  <CheckCircle2Icon className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">{stats.ok}</div>
                  <div className="text-xs text-neutral-500 uppercase tracking-wide">OK</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-neutral-200 p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-red-50">
                  <XCircleIcon className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-600">{stats.defects}</div>
                  <div className="text-xs text-neutral-500 uppercase tracking-wide">Defects</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-neutral-200 p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-amber-50">
                  <AlertTriangleIcon className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-amber-600">{stats.potential}</div>
                  <div className="text-xs text-neutral-500 uppercase tracking-wide">Potential</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-neutral-200 p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-50">
                  <AlertCircleIcon className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-600">{stats.pending}</div>
                  <div className="text-xs text-neutral-500 uppercase tracking-wide">Pending</div>
                </div>
              </div>
            </div>
          </div>

          {/* Filter Chips */}
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-medium text-neutral-700">Filter:</span>
            <button
              onClick={() => setStatusFilter('')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                statusFilter === ''
                  ? 'bg-primary-600 text-white shadow-md'
                  : 'bg-white text-neutral-700 border border-neutral-300 hover:border-primary-300'
              }`}
            >
              All Pieces ({stats.totalPieces})
            </button>
            <button
              onClick={() => setStatusFilter('ok')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                statusFilter === 'ok'
                  ? 'bg-green-600 text-white shadow-md'
                  : 'bg-white text-neutral-700 border border-neutral-300 hover:border-green-300'
              }`}
            >
              OK ({stats.ok})
            </button>
            <button
              onClick={() => setStatusFilter('defect')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                statusFilter === 'defect'
                  ? 'bg-red-600 text-white shadow-md'
                  : 'bg-white text-neutral-700 border border-neutral-300 hover:border-red-300'
              }`}
            >
              Defects ({stats.defects})
            </button>
            <button
              onClick={() => setStatusFilter('potential_defect')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                statusFilter === 'potential_defect'
                  ? 'bg-amber-600 text-white shadow-md'
                  : 'bg-white text-neutral-700 border border-neutral-300 hover:border-amber-300'
              }`}
            >
              Potential ({stats.potential})
            </button>
            <button
              onClick={() => setStatusFilter('pending_review')}
              className={`px-4 py-2 rounded-full text-sm font-medium transition ${
                statusFilter === 'pending_review'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-white text-neutral-700 border border-neutral-300 hover:border-blue-300'
              }`}
            >
              Pending ({stats.pending})
            </button>
          </div>
        </div>

        {/* Pieces Grid */}
        {pieceGroups.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-lg border border-neutral-200 p-16 text-center">
            <div className="text-8xl mb-6">📸</div>
            <h3 className="text-2xl font-bold text-neutral-900 mb-3">No pieces found</h3>
            <p className="text-neutral-600 text-lg">
              {statusFilter ? 'Try changing the filter above' : 'No pieces have been photographed yet'}
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {pieceGroups.map((piece) => {
              const isExpanded = expandedPieces.has(`piece-${piece.pieceNumber}`)
              const displayPhotos = isExpanded ? piece.photos : piece.photos.slice(0, 4)

              return (
                <div
                  key={`piece-${piece.pieceNumber}`}
                  className="bg-white rounded-2xl shadow-lg border border-neutral-200 overflow-hidden"
                >
                  {/* Piece Header */}
                  <div className="p-6 border-b border-neutral-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <button
                          onClick={() => togglePieceExpansion(`piece-${piece.pieceNumber}`)}
                          className="p-2 rounded-lg hover:bg-neutral-100 transition"
                        >
                          {isExpanded ? (
                            <ChevronDownIcon className="h-5 w-5 text-neutral-600" />
                          ) : (
                            <ChevronRightIcon className="h-5 w-5 text-neutral-600" />
                          )}
                        </button>

                        <div>
                          <h3 className="text-xl font-bold text-neutral-900 flex items-center gap-3">
                            <PackageIcon className="h-5 w-5 text-primary-600" />
                            Piece #{piece.pieceNumber}
                            <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold ${getStatusColor(piece.status)}`}>
                              {getStatusIcon(piece.status)}
                              {piece.status.replace('_', ' ').toUpperCase()}
                            </span>
                          </h3>
                          <p className="text-sm text-neutral-600 mt-1">
                            {piece.photos.length} photo{piece.photos.length !== 1 ? 's' : ''} •
                            First: {new Date(piece.firstPhotoTime).toLocaleTimeString()} •
                            Last: {new Date(piece.lastPhotoTime).toLocaleTimeString()}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {piece.measurements && (
                          <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 rounded-lg">
                            <RulerIcon className="h-4 w-4 text-blue-600" />
                            <span className="text-sm font-medium text-blue-900">Measured</span>
                          </div>
                        )}
                        {piece.defectCount > 0 && (
                          <div className="flex items-center gap-2 px-3 py-2 bg-red-50 rounded-lg">
                            <AlertTriangleIcon className="h-4 w-4 text-red-600" />
                            <span className="text-sm font-medium text-red-900">{piece.defectCount} Issue{piece.defectCount !== 1 ? 's' : ''}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Measurements info if available */}
                    {piece.measurements && (
                      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                        <div className="flex items-center gap-6 text-sm">
                          <div>
                            <span className="text-neutral-600">Type:</span>
                            <span className="ml-2 font-medium text-neutral-900">{piece.measurements.garment_type}</span>
                          </div>
                          <div>
                            <span className="text-neutral-600">Size:</span>
                            <span className="ml-2 font-medium text-neutral-900">{piece.measurements.size_estimate}</span>
                          </div>
                          <div>
                            <span className="text-neutral-600">Chest:</span>
                            <span className="ml-2 font-medium text-neutral-900">{piece.measurements.chest_width_cm?.toFixed(1)}cm</span>
                          </div>
                          <div>
                            <span className="text-neutral-600">Length:</span>
                            <span className="ml-2 font-medium text-neutral-900">{piece.measurements.body_length_cm?.toFixed(1)}cm</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Photos Grid */}
                  <div className="p-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                      {displayPhotos.map((photo: any, index: number) => (
                        <button
                          key={photo.id}
                          onClick={() => handlePhotoClick(photo, piece)}
                          className="group relative aspect-square bg-neutral-100 rounded-lg overflow-hidden hover:ring-2 hover:ring-primary-500 transition"
                        >
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={photo.url || '/placeholder-image.jpg'}
                            alt={`Piece #${piece.pieceNumber} - Photo ${index + 1}`}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                            onError={(e) => {
                              e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="400"%3E%3Crect fill="%23e2e8f0" width="400" height="400"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%2394a3b8" font-size="64"%3E📷%3C/text%3E%3C/svg%3E'
                            }}
                          />

                          {/* Photo number badge */}
                          <div className="absolute top-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded-full">
                            #{index + 1}
                          </div>

                          {/* First photo indicator */}
                          {index === 0 && (
                            <div className="absolute top-2 right-2 bg-primary-600 text-white text-xs px-2 py-1 rounded-full font-bold">
                              First
                            </div>
                          )}

                          {/* Hover overlay */}
                          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition">
                            <div className="absolute bottom-2 left-2 right-2 text-white text-xs">
                              <div className="font-medium">{new Date(photo.capturedAt).toLocaleTimeString()}</div>
                            </div>
                          </div>
                        </button>
                      ))}

                      {/* Show more button */}
                      {!isExpanded && piece.photos.length > 4 && (
                        <button
                          onClick={() => togglePieceExpansion(`piece-${piece.pieceNumber}`)}
                          className="aspect-square bg-neutral-100 rounded-lg flex items-center justify-center hover:bg-neutral-200 transition"
                        >
                          <div className="text-center">
                            <div className="text-2xl font-bold text-neutral-600">+{piece.photos.length - 4}</div>
                            <div className="text-xs text-neutral-500">more photos</div>
                          </div>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Enhanced Photo Zoom Viewer with Navigation */}
        {selectedPhoto && selectedPiece && (
          <>
            <ImageZoomViewer
              src={selectedPhoto.url || '/placeholder-image.jpg'}
              alt={`Piece #${selectedPhoto.pieceNumber} - Photo ${currentPhotoIndex + 1}`}
              onClose={() => {
                setSelectedPhoto(null)
                setSelectedPiece(null)
              }}
              title={`Piece #${selectedPhoto.pieceNumber} - Photo ${currentPhotoIndex + 1} of ${pieceGroups.find(g => `piece-${g.pieceNumber}` === selectedPiece)?.photos.length || 1}`}
              description={`${selectedPhoto.pieceStatus?.replace('_', ' ').toUpperCase()} • Captured ${new Date(selectedPhoto.capturedAt).toLocaleString()}`}
              annotation={`Photo ID: ${selectedPhoto.id.substring(0, 8)}... • File: ${selectedPhoto.filePath?.split('/').pop() || 'N/A'}`}
            />

            {/* Photo Navigation Overlay */}
            {(() => {
              const piece = pieceGroups.find(g => `piece-${g.pieceNumber}` === selectedPiece)
              return piece && piece.photos.length > 1 && (
                <>
                  <button
                    onClick={() => navigatePhoto('prev')}
                    className="fixed left-8 top-1/2 -translate-y-1/2 z-[101] p-4 rounded-full bg-black/50 hover:bg-black/70 text-white transition backdrop-blur-sm"
                    aria-label="Previous photo"
                  >
                    <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => navigatePhoto('next')}
                    className="fixed right-8 top-1/2 -translate-y-1/2 z-[101] p-4 rounded-full bg-black/50 hover:bg-black/70 text-white transition backdrop-blur-sm"
                    aria-label="Next photo"
                  >
                    <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </>
              )
            })()}
          </>
        )}
      </div>
    </div>
  )
}