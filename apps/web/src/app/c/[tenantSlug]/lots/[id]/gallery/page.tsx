'use client'

import { useCallback, useEffect, useState, useMemo } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import Link from 'next/link'
import { ArrowLeftIcon, CheckCircle2Icon, XCircleIcon, AlertCircleIcon, ImageIcon, ZoomInIcon, XIcon } from 'lucide-react'

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

  // Calculate statistics
  const stats = useMemo(() => {
    if (!gallery?.photos) return { total: 0, ok: 0, defects: 0, potential: 0, pending: 0 }

    const total = gallery.photos.length
    const ok = gallery.photos.filter((p: any) => p.pieceStatus === 'ok').length
    const defects = gallery.photos.filter((p: any) => p.pieceStatus === 'defect').length
    const potential = gallery.photos.filter((p: any) => p.pieceStatus === 'potential_defect').length
    const pending = gallery.photos.filter((p: any) => p.pieceStatus === 'pending_review').length

    return { total, ok, defects, potential, pending }
  }, [gallery])

  const handlePhotoClick = (photo: any, index: number) => {
    setSelectedPhoto(photo)
    setCurrentPhotoIndex(index)
  }

  const navigatePhoto = useCallback((direction: 'prev' | 'next') => {
    if (!gallery?.photos) return
    const newIndex = direction === 'prev'
      ? (currentPhotoIndex - 1 + gallery.photos.length) % gallery.photos.length
      : (currentPhotoIndex + 1) % gallery.photos.length
    setCurrentPhotoIndex(newIndex)
    setSelectedPhoto(gallery.photos[newIndex])
  }, [gallery, currentPhotoIndex])

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
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedPhoto, navigatePhoto])

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
                <ImageIcon className="h-10 w-10 text-primary-600" />
                Inspection Gallery
              </h1>
              <p className="text-neutral-600 text-lg">
                Visual record of {stats.total} inspected pieces
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
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-neutral-200 p-4 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary-50">
                  <ImageIcon className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-neutral-900">{stats.total}</div>
                  <div className="text-xs text-neutral-500 uppercase tracking-wide">Total Photos</div>
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
                  <div className="text-xs text-neutral-500 uppercase tracking-wide">OK Pieces</div>
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
                  <AlertCircleIcon className="h-5 w-5 text-amber-600" />
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
              All ({stats.total})
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

        {/* Gallery Grid */}
        {gallery.photos.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-lg border border-neutral-200 p-16 text-center">
            <div className="text-8xl mb-6">📸</div>
            <h3 className="text-2xl font-bold text-neutral-900 mb-3">No photos found</h3>
            <p className="text-neutral-600 text-lg">
              {statusFilter ? 'Try changing the filter above' : 'No photos have been captured yet'}
            </p>
          </div>
        ) : (
          <div className="columns-2 md:columns-3 lg:columns-4 gap-4 space-y-4">
            {gallery.photos.map((photo: any, index: number) => (
              <button
                key={photo.id}
                onClick={() => handlePhotoClick(photo, index)}
                className="group relative w-full break-inside-avoid mb-4 bg-white rounded-xl overflow-hidden shadow-md hover:shadow-2xl transition-all duration-300 border border-neutral-200"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={photo.url || '/placeholder-image.jpg'}
                  alt={`Piece #${photo.pieceNumber}`}
                  className="w-full h-auto object-cover transition-transform duration-300 group-hover:scale-105"
                  onError={(e) => {
                    e.currentTarget.src =
                      'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="400"%3E%3Crect fill="%23e2e8f0" width="400" height="400"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%2394a3b8" font-size="64"%3E📷%3C/text%3E%3C/svg%3E'
                  }}
                />

                {/* Status Badge */}
                <div className="absolute top-3 right-3">
                  <span
                    className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold shadow-lg ${
                      photo.pieceStatus === 'ok'
                        ? 'bg-green-500 text-white'
                        : photo.pieceStatus === 'defect'
                        ? 'bg-red-500 text-white'
                        : photo.pieceStatus === 'potential_defect'
                        ? 'bg-amber-500 text-white'
                        : 'bg-blue-500 text-white'
                    }`}
                  >
                    {photo.pieceStatus === 'ok' && <CheckCircle2Icon className="h-3 w-3" />}
                    {photo.pieceStatus === 'defect' && <XCircleIcon className="h-3 w-3" />}
                    {(photo.pieceStatus === 'potential_defect' || photo.pieceStatus === 'pending_review') && (
                      <AlertCircleIcon className="h-3 w-3" />
                    )}
                    {photo.pieceStatus?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
                  </span>
                </div>

                {/* Hover Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <div className="absolute bottom-0 left-0 right-0 p-4 text-white">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-bold mb-1">Piece #{photo.pieceNumber}</div>
                        <div className="text-xs text-neutral-200">
                          {new Date(photo.capturedAt).toLocaleString()}
                        </div>
                      </div>
                      <ZoomInIcon className="h-5 w-5" />
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Enhanced Photo Lightbox Modal */}
        {selectedPhoto && (
        <div
          className="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4 backdrop-blur-sm"
          onClick={() => setSelectedPhoto(null)}
        >
          <div className="max-w-7xl w-full" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="text-white">
                <h2 className="text-3xl font-bold flex items-center gap-3">
                  Piece #{selectedPhoto.pieceNumber}
                  <span
                    className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold ${
                      selectedPhoto.pieceStatus === 'ok'
                        ? 'bg-green-500'
                        : selectedPhoto.pieceStatus === 'defect'
                        ? 'bg-red-500'
                        : selectedPhoto.pieceStatus === 'potential_defect'
                        ? 'bg-amber-500'
                        : 'bg-blue-500'
                    }`}
                  >
                    {selectedPhoto.pieceStatus === 'ok' && <CheckCircle2Icon className="h-4 w-4" />}
                    {selectedPhoto.pieceStatus === 'defect' && <XCircleIcon className="h-4 w-4" />}
                    {(selectedPhoto.pieceStatus === 'potential_defect' || selectedPhoto.pieceStatus === 'pending_review') && (
                      <AlertCircleIcon className="h-4 w-4" />
                    )}
                    {selectedPhoto.pieceStatus?.replace('_', ' ').toUpperCase()}
                  </span>
                </h2>
                <p className="text-neutral-300 mt-2 text-sm">
                  Captured {new Date(selectedPhoto.capturedAt).toLocaleString()} • Photo {currentPhotoIndex + 1} of {gallery.photos.length}
                </p>
              </div>
              <button
                onClick={() => setSelectedPhoto(null)}
                className="p-3 rounded-full bg-white/10 hover:bg-white/20 text-white transition"
              >
                <XIcon className="h-6 w-6" />
              </button>
            </div>

            {/* Main Image */}
            <div className="relative bg-neutral-900 rounded-2xl overflow-hidden shadow-2xl">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={selectedPhoto.url || '/placeholder-image.jpg'}
                alt={`Piece #${selectedPhoto.pieceNumber}`}
                className="w-full h-auto max-h-[75vh] object-contain mx-auto"
                onError={(e) => {
                  e.currentTarget.src =
                    'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="1200" height="900"%3E%3Crect fill="%231f2937" width="1200" height="900"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%239ca3af" font-size="96"%3E📷%3C/text%3E%3C/svg%3E'
                }}
              />

              {/* Navigation Arrows */}
              {gallery.photos.length > 1 && (
                <>
                  <button
                    onClick={() => navigatePhoto('prev')}
                    className="absolute left-4 top-1/2 -translate-y-1/2 p-4 rounded-full bg-black/50 hover:bg-black/70 text-white transition backdrop-blur-sm"
                  >
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => navigatePhoto('next')}
                    className="absolute right-4 top-1/2 -translate-y-1/2 p-4 rounded-full bg-black/50 hover:bg-black/70 text-white transition backdrop-blur-sm"
                  >
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </>
              )}
            </div>

            {/* Footer Info */}
            <div className="mt-4 bg-white/10 backdrop-blur-md rounded-xl p-4">
              <div className="flex items-center justify-between text-sm text-white">
                <div className="flex items-center gap-6">
                  <div>
                    <span className="text-neutral-400">Photo ID:</span>
                    <span className="ml-2 font-mono text-xs">{selectedPhoto.id.substring(0, 8)}...</span>
                  </div>
                  <div>
                    <span className="text-neutral-400">File:</span>
                    <span className="ml-2 font-mono text-xs">{selectedPhoto.filePath?.split('/').pop() || 'N/A'}</span>
                  </div>
                </div>
                <div className="text-neutral-400 text-xs">
                  Use ← → arrow keys to navigate
                </div>
              </div>
            </div>
          </div>
        </div>
        )}
      </div>
    </div>
  )
}