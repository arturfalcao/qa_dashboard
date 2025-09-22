'use client'

import { useState, useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { InspectionPhoto, PhotoAnnotation, PhotoAngle, DefectType, DefectSeverity } from '@qa-dashboard/shared'
import { apiClient } from '@/lib/api'
import { cn } from '@/lib/utils'
import { ZoomIn, ZoomOut, RotateCcw, Eye, Plus, Edit, Trash2, AlertTriangle } from 'lucide-react'
import Image from 'next/image'

interface EnhancedPhotoGalleryProps {
  inspectionId: string
  onAnnotationCreate?: (annotation: PhotoAnnotation) => void
  onAnnotationUpdate?: (annotation: PhotoAnnotation) => void
  onAnnotationDelete?: (annotationId: string) => void
  readonly?: boolean
}

interface AnnotationForm {
  x: number
  y: number
  comment: string
  defectType?: DefectType
  severity?: DefectSeverity
}

const PHOTO_ANGLE_LABELS: Record<PhotoAngle, string> = {
  [PhotoAngle.FRONT]: 'Front View',
  [PhotoAngle.BACK]: 'Back View',
  [PhotoAngle.SIDE_LEFT]: 'Left Side',
  [PhotoAngle.SIDE_RIGHT]: 'Right Side',
  [PhotoAngle.DETAIL_MACRO]: 'Detail/Macro',
  [PhotoAngle.HANGING]: 'Hanging',
  [PhotoAngle.FLAT_LAY]: 'Flat Lay',
}

const SEVERITY_COLORS: Record<DefectSeverity, string> = {
  [DefectSeverity.CRITICAL]: 'bg-red-500 border-red-600',
  [DefectSeverity.MAJOR]: 'bg-orange-500 border-orange-600',
  [DefectSeverity.MINOR]: 'bg-yellow-500 border-yellow-600',
}

export function EnhancedPhotoGallery({
  inspectionId,
  onAnnotationCreate,
  onAnnotationUpdate,
  onAnnotationDelete,
  readonly = false
}: EnhancedPhotoGalleryProps) {
  const [selectedPhoto, setSelectedPhoto] = useState<InspectionPhoto | null>(null)
  const [zoom, setZoom] = useState(1)
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [lastPanPoint, setLastPanPoint] = useState({ x: 0, y: 0 })
  const [annotationMode, setAnnotationMode] = useState(false)
  const [pendingAnnotation, setPendingAnnotation] = useState<AnnotationForm | null>(null)
  const [selectedAnnotation, setSelectedAnnotation] = useState<PhotoAnnotation | null>(null)

  const imageRef = useRef<HTMLImageElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Fetch photos for inspection
  const { data: photos = [], isLoading } = useQuery({
    queryKey: ['inspection-photos', inspectionId],
    queryFn: () => apiClient.getPhotosForInspection(inspectionId),
    enabled: !!inspectionId,
  })

  // Fetch annotations for selected photo
  const { data: annotations = [] } = useQuery({
    queryKey: ['photo-annotations', selectedPhoto?.id],
    queryFn: () => selectedPhoto ? apiClient.getAnnotationsForPhoto(selectedPhoto.id) : Promise.resolve([]),
    enabled: !!selectedPhoto?.id,
  })

  const handlePhotoSelect = useCallback((photo: InspectionPhoto) => {
    setSelectedPhoto(photo)
    setZoom(1)
    setPanOffset({ x: 0, y: 0 })
    setAnnotationMode(false)
    setPendingAnnotation(null)
    setSelectedAnnotation(null)
  }, [])

  const handleZoomIn = useCallback(() => {
    setZoom(prev => Math.min(prev * 1.5, 5))
  }, [])

  const handleZoomOut = useCallback(() => {
    setZoom(prev => Math.max(prev / 1.5, 0.5))
  }, [])

  const handleReset = useCallback(() => {
    setZoom(1)
    setPanOffset({ x: 0, y: 0 })
  }, [])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (zoom > 1) {
      setIsPanning(true)
      setLastPanPoint({ x: e.clientX, y: e.clientY })
    }
  }, [zoom])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isPanning && zoom > 1) {
      const deltaX = e.clientX - lastPanPoint.x
      const deltaY = e.clientY - lastPanPoint.y

      setPanOffset(prev => ({
        x: prev.x + deltaX,
        y: prev.y + deltaY,
      }))

      setLastPanPoint({ x: e.clientX, y: e.clientY })
    }
  }, [isPanning, lastPanPoint, zoom])

  const handleMouseUp = useCallback(() => {
    setIsPanning(false)
  }, [])

  const handleImageClick = useCallback((e: React.MouseEvent) => {
    if (!annotationMode || !selectedPhoto || readonly) return

    const rect = imageRef.current?.getBoundingClientRect()
    if (!rect) return

    const x = ((e.clientX - rect.left) / rect.width) * 100
    const y = ((e.clientY - rect.top) / rect.height) * 100

    setPendingAnnotation({
      x: Math.round(x * 100) / 100,
      y: Math.round(y * 100) / 100,
      comment: '',
      defectType: DefectType.OTHER,
      severity: DefectSeverity.MINOR,
    })
  }, [annotationMode, selectedPhoto, readonly])

  const handleAnnotationSubmit = useCallback(async () => {
    if (!pendingAnnotation || !selectedPhoto) return

    try {
      const annotation = await apiClient.createAnnotation(
        selectedPhoto.id,
        pendingAnnotation.x,
        pendingAnnotation.y,
        pendingAnnotation.comment,
        pendingAnnotation.defectType,
        pendingAnnotation.severity
      )

      onAnnotationCreate?.(annotation)
      setPendingAnnotation(null)
      setAnnotationMode(false)
    } catch (error) {
      console.error('Failed to create annotation:', error)
    }
  }, [pendingAnnotation, selectedPhoto, onAnnotationCreate])

  const handleAnnotationDelete = useCallback(async (annotationId: string) => {
    try {
      await apiClient.deleteAnnotation(annotationId)
      onAnnotationDelete?.(annotationId)
      setSelectedAnnotation(null)
    } catch (error) {
      console.error('Failed to delete annotation:', error)
    }
  }, [onAnnotationDelete])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (photos.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <div className="text-center">
          <Eye className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No photos available</h3>
          <p className="mt-1 text-sm text-gray-500">Photos will appear here when uploaded</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Photo Selection Tabs */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex flex-wrap gap-2">
          {photos.map((photo) => (
            <button
              key={photo.id}
              onClick={() => handlePhotoSelect(photo)}
              className={cn(
                'px-3 py-2 text-sm font-medium rounded-md transition-colors',
                selectedPhoto?.id === photo.id
                  ? 'bg-primary-100 text-primary-700 border border-primary-200'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {PHOTO_ANGLE_LABELS[photo.angle]}
            </button>
          ))}
        </div>
      </div>

      {selectedPhoto && (
        <>
          {/* Controls */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <div className="flex items-center space-x-2">
              <button
                onClick={handleZoomIn}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={handleZoomOut}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={handleReset}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                title="Reset View"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <div className="text-sm text-gray-500 ml-2">
                {Math.round(zoom * 100)}%
              </div>
            </div>

            {!readonly && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setAnnotationMode(!annotationMode)}
                  className={cn(
                    'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                    annotationMode
                      ? 'bg-primary-100 text-primary-700 border border-primary-200'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  )}
                >
                  <Plus className="w-4 h-4 mr-1 inline" />
                  Add Annotation
                </button>
              </div>
            )}
          </div>

          {/* Photo Viewer */}
          <div
            ref={containerRef}
            className="relative overflow-hidden bg-gray-900"
            style={{ height: '600px' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <div
              className="relative w-full h-full flex items-center justify-center"
              style={{
                transform: `scale(${zoom}) translate(${panOffset.x}px, ${panOffset.y}px)`,
                cursor: zoom > 1 ? (isPanning ? 'grabbing' : 'grab') : annotationMode ? 'crosshair' : 'default',
              }}
              onClick={handleImageClick}
            >
              <Image
                ref={imageRef}
                src={selectedPhoto.photoUrl || ''}
                alt={`${PHOTO_ANGLE_LABELS[selectedPhoto.angle]} view`}
                width={800}
                height={600}
                className="max-w-full max-h-full object-contain"
                draggable={false}
              />

              {/* Annotations */}
              {annotations.map((annotation) => (
                <button
                  key={annotation.id}
                  className={cn(
                    'absolute w-6 h-6 rounded-full border-2 transform -translate-x-1/2 -translate-y-1/2 z-10',
                    annotation.severity
                      ? SEVERITY_COLORS[annotation.severity]
                      : 'bg-blue-500 border-blue-600',
                    selectedAnnotation?.id === annotation.id && 'ring-2 ring-white'
                  )}
                  style={{
                    left: `${annotation.x}%`,
                    top: `${annotation.y}%`,
                  }}
                  onClick={(e) => {
                    e.stopPropagation()
                    setSelectedAnnotation(annotation)
                  }}
                  title={annotation.comment}
                >
                  {annotation.severity === DefectSeverity.CRITICAL && (
                    <AlertTriangle className="w-3 h-3 text-white m-auto" />
                  )}
                </button>
              ))}

              {/* Pending Annotation */}
              {pendingAnnotation && (
                <div
                  className="absolute w-6 h-6 bg-green-500 border-2 border-green-600 rounded-full transform -translate-x-1/2 -translate-y-1/2 z-10"
                  style={{
                    left: `${pendingAnnotation.x}%`,
                    top: `${pendingAnnotation.y}%`,
                  }}
                />
              )}
            </div>
          </div>

          {/* Annotation Sidebar */}
          {(selectedAnnotation || pendingAnnotation) && (
            <div className="border-t border-gray-200 p-4 bg-gray-50">
              {pendingAnnotation && (
                <div className="space-y-3">
                  <h4 className="font-medium text-gray-900">Add Annotation</h4>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Comment
                    </label>
                    <textarea
                      value={pendingAnnotation.comment}
                      onChange={(e) => setPendingAnnotation(prev => prev ? { ...prev, comment: e.target.value } : null)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                      rows={2}
                      placeholder="Describe the defect or issue..."
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Defect Type
                      </label>
                      <select
                        value={pendingAnnotation.defectType}
                        onChange={(e) => setPendingAnnotation(prev => prev ? { ...prev, defectType: e.target.value as DefectType } : null)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                      >
                        {Object.values(DefectType).map((type) => (
                          <option key={type} value={type}>
                            {type.replace('_', ' ').toUpperCase()}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Severity
                      </label>
                      <select
                        value={pendingAnnotation.severity}
                        onChange={(e) => setPendingAnnotation(prev => prev ? { ...prev, severity: e.target.value as DefectSeverity } : null)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                      >
                        {Object.values(DefectSeverity).map((severity) => (
                          <option key={severity} value={severity}>
                            {severity.toUpperCase()}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={handleAnnotationSubmit}
                      disabled={!pendingAnnotation.comment.trim()}
                      className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Save Annotation
                    </button>
                    <button
                      onClick={() => {
                        setPendingAnnotation(null)
                        setAnnotationMode(false)
                      }}
                      className="px-4 py-2 bg-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-400"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {selectedAnnotation && !pendingAnnotation && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-gray-900">Annotation Details</h4>
                    {!readonly && (
                      <div className="flex space-x-1">
                        <button
                          onClick={() => handleAnnotationDelete(selectedAnnotation.id)}
                          className="p-1 text-red-500 hover:text-red-700"
                          title="Delete annotation"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="text-sm text-gray-700">
                    <div className="mb-2">
                      <strong>Comment:</strong> {selectedAnnotation.comment}
                    </div>
                    {selectedAnnotation.defectType && (
                      <div className="mb-2">
                        <strong>Type:</strong> {selectedAnnotation.defectType.replace('_', ' ').toUpperCase()}
                      </div>
                    )}
                    {selectedAnnotation.severity && (
                      <div className="mb-2">
                        <strong>Severity:</strong>
                        <span className={cn(
                          'ml-2 px-2 py-1 text-xs font-medium rounded-full text-white',
                          selectedAnnotation.severity === DefectSeverity.CRITICAL && 'bg-red-500',
                          selectedAnnotation.severity === DefectSeverity.MAJOR && 'bg-orange-500',
                          selectedAnnotation.severity === DefectSeverity.MINOR && 'bg-yellow-500'
                        )}>
                          {selectedAnnotation.severity.toUpperCase()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}