'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import Link from 'next/link'

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

  useEffect(() => {
    loadGallery()
  }, [lotId, statusFilter])

  const loadGallery = async () => {
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
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error || !gallery) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-800">{error || 'Gallery not found'}</p>
          <Link
            href={`/c/${tenantSlug}/lots/${lotId}`}
            className="mt-4 inline-block text-primary-600 hover:text-primary-800 font-medium"
          >
            ← Back to Lot
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-slate-600 mb-2">
          <Link href={`/c/${tenantSlug}/lots`} className="hover:text-slate-900">
            Lots
          </Link>
          <span>/</span>
          <Link href={`/c/${tenantSlug}/lots/${lotId}`} className="hover:text-slate-900">
            {lotId.substring(0, 8)}
          </Link>
          <span>/</span>
          <span className="text-slate-900">Gallery</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Photo Gallery</h1>
            <p className="text-slate-600 mt-1">{gallery.totalPhotos} photos captured</p>
          </div>
          <Link
            href={`/c/${tenantSlug}/lots/${lotId}`}
            className="px-4 py-2 border border-slate-300 rounded-xl hover:bg-slate-50 font-medium transition"
          >
            ← Back to Lot
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4 mb-6">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-slate-700">Filter by status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-slate-300 rounded-xl text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200"
          >
            <option value="">All Photos</option>
            <option value="ok">OK Pieces</option>
            <option value="defect">Defects</option>
            <option value="potential_defect">Potential Defects</option>
            <option value="pending_review">Pending Review</option>
          </select>
        </div>
      </div>

      {/* Gallery Grid */}
      {gallery.photos.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-12 text-center">
          <div className="text-6xl mb-4">📸</div>
          <h3 className="text-lg font-semibold text-slate-900 mb-2">No photos found</h3>
          <p className="text-slate-600">
            {statusFilter ? 'Try changing the filter' : 'No photos have been captured yet'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {gallery.photos.map((photo: any) => (
            <button
              key={photo.id}
              onClick={() => setSelectedPhoto(photo)}
              className="group relative aspect-square bg-slate-100 rounded-xl overflow-hidden shadow-md hover:shadow-xl transition"
            >
              <img
                src={`/api/photos/${photo.filePath}`}
                alt={`Piece #${photo.pieceNumber}`}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.currentTarget.src =
                    'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23e2e8f0" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%2394a3b8" font-size="48"%3E📷%3C/text%3E%3C/svg%3E'
                }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition">
                <div className="absolute bottom-0 left-0 right-0 p-3 text-white">
                  <div className="text-sm font-semibold">Piece #{photo.pieceNumber}</div>
                  <div className="text-xs mt-1">
                    {new Date(photo.capturedAt).toLocaleString()}
                  </div>
                  {photo.pieceStatus && (
                    <span
                      className={`inline-block mt-2 px-2 py-0.5 rounded text-xs font-semibold ${
                        photo.pieceStatus === 'ok'
                          ? 'bg-green-500'
                          : photo.pieceStatus === 'defect'
                          ? 'bg-red-500'
                          : photo.pieceStatus === 'potential_defect'
                          ? 'bg-amber-500'
                          : 'bg-slate-500'
                      }`}
                    >
                      {photo.pieceStatus.replace('_', ' ')}
                    </span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Photo Detail Modal */}
      {selectedPhoto && (
        <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50 p-4">
          <div className="max-w-6xl w-full">
            <div className="flex items-center justify-between mb-4">
              <div className="text-white">
                <h2 className="text-2xl font-semibold">Piece #{selectedPhoto.pieceNumber}</h2>
                <p className="text-sm text-slate-300 mt-1">
                  {new Date(selectedPhoto.capturedAt).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => setSelectedPhoto(null)}
                className="text-white hover:text-slate-300 transition"
              >
                <span className="text-4xl">×</span>
              </button>
            </div>

            <div className="bg-white rounded-xl overflow-hidden">
              <img
                src={`/api/photos/${selectedPhoto.filePath}`}
                alt={`Piece #${selectedPhoto.pieceNumber}`}
                className="w-full h-auto max-h-[70vh] object-contain"
                onError={(e) => {
                  e.currentTarget.src =
                    'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="800" height="600"%3E%3Crect fill="%23e2e8f0" width="800" height="600"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%2394a3b8" font-size="64"%3E📷%3C/text%3E%3C/svg%3E'
                }}
              />
              <div className="p-4 bg-slate-50 border-t border-slate-200">
                <div className="flex items-center gap-4 text-sm">
                  <div>
                    <span className="text-slate-500">Status:</span>
                    <span
                      className={`ml-2 px-2 py-1 rounded font-semibold ${
                        selectedPhoto.pieceStatus === 'ok'
                          ? 'bg-green-100 text-green-800'
                          : selectedPhoto.pieceStatus === 'defect'
                          ? 'bg-red-100 text-red-800'
                          : selectedPhoto.pieceStatus === 'potential_defect'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-100 text-slate-800'
                      }`}
                    >
                      {selectedPhoto.pieceStatus?.replace('_', ' ') || 'Unknown'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500">Photo ID:</span>
                    <span className="ml-2 text-slate-900 font-mono text-xs">
                      {selectedPhoto.id.substring(0, 8)}...
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}