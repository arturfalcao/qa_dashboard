'use client'

import React, { useState, useRef, useEffect, WheelEvent, MouseEvent, TouchEvent } from 'react'
import {
  XIcon,
  ZoomInIcon,
  ZoomOutIcon,
  MaximizeIcon,
  MoveIcon,
  RotateCwIcon
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ImageZoomViewerProps {
  src: string
  alt?: string
  annotation?: string
  onClose: () => void
  title?: string
  description?: string
}

export function ImageZoomViewer({
  src,
  alt = 'Image',
  annotation,
  onClose,
  title,
  description
}: ImageZoomViewerProps) {
  const [zoom, setZoom] = useState(1)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(false)

  const containerRef = useRef<HTMLDivElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)

  // Zoom limits
  const MIN_ZOOM = 0.5
  const MAX_ZOOM = 5
  const ZOOM_STEP = 0.25

  // Reset zoom and position
  const resetView = () => {
    setZoom(1)
    setPosition({ x: 0, y: 0 })
  }

  // Fit to screen
  const fitToScreen = () => {
    if (!imageRef.current || !containerRef.current) return

    const container = containerRef.current.getBoundingClientRect()
    const img = imageRef.current

    const scaleX = container.width / img.naturalWidth
    const scaleY = container.height / img.naturalHeight
    const scale = Math.min(scaleX, scaleY, 1) * 0.9 // 90% to leave some padding

    setZoom(scale)
    setPosition({ x: 0, y: 0 })
  }

  // Zoom in/out functions
  const zoomIn = () => {
    setZoom((prev) => Math.min(prev + ZOOM_STEP, MAX_ZOOM))
  }

  const zoomOut = () => {
    setZoom((prev) => Math.max(prev - ZOOM_STEP, MIN_ZOOM))
  }

  // Handle mouse wheel zoom
  const handleWheel = (e: WheelEvent<HTMLDivElement>) => {
    e.preventDefault()

    const delta = e.deltaY * -0.001
    const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom + delta))

    setZoom(newZoom)
  }

  // Handle drag start
  const handleMouseDown = (e: MouseEvent<HTMLDivElement>) => {
    if (e.button !== 0) return // Only left click

    e.preventDefault()
    setIsDragging(true)
    setDragStart({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    })
  }

  // Handle drag move
  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    if (!isDragging) return

    e.preventDefault()
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    })
  }

  // Handle drag end
  const handleMouseUp = () => {
    setIsDragging(false)
  }

  // Touch support for mobile
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null)
  const [lastDistance, setLastDistance] = useState<number | null>(null)

  const getTouchDistance = (touches: React.TouchList) => {
    if (touches.length < 2) return null
    const dx = touches[0].clientX - touches[1].clientX
    const dy = touches[0].clientY - touches[1].clientY
    return Math.sqrt(dx * dx + dy * dy)
  }

  const handleTouchStart = (e: TouchEvent<HTMLDivElement>) => {
    if (e.touches.length === 1) {
      // Single touch - pan
      setTouchStart({
        x: e.touches[0].clientX - position.x,
        y: e.touches[0].clientY - position.y
      })
    } else if (e.touches.length === 2) {
      // Two fingers - zoom
      const distance = getTouchDistance(e.touches)
      setLastDistance(distance)
    }
  }

  const handleTouchMove = (e: TouchEvent<HTMLDivElement>) => {
    e.preventDefault()

    if (e.touches.length === 1 && touchStart) {
      // Pan
      setPosition({
        x: e.touches[0].clientX - touchStart.x,
        y: e.touches[0].clientY - touchStart.y
      })
    } else if (e.touches.length === 2) {
      // Pinch zoom
      const distance = getTouchDistance(e.touches)
      if (distance && lastDistance) {
        const delta = (distance - lastDistance) * 0.01
        const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom + delta))
        setZoom(newZoom)
        setLastDistance(distance)
      }
    }
  }

  const handleTouchEnd = () => {
    setTouchStart(null)
    setLastDistance(null)
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch(e.key) {
        case 'Escape':
          onClose()
          break
        case '+':
        case '=':
          zoomIn()
          break
        case '-':
        case '_':
          zoomOut()
          break
        case '0':
          resetView()
          break
        case 'f':
          fitToScreen()
          break
        case 'ArrowUp':
          setPosition(prev => ({ ...prev, y: prev.y + 50 }))
          break
        case 'ArrowDown':
          setPosition(prev => ({ ...prev, y: prev.y - 50 }))
          break
        case 'ArrowLeft':
          setPosition(prev => ({ ...prev, x: prev.x + 50 }))
          break
        case 'ArrowRight':
          setPosition(prev => ({ ...prev, x: prev.x - 50 }))
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-sm">
      {/* Header */}
      <div className="absolute left-0 right-0 top-0 z-10 bg-gradient-to-b from-black/80 to-transparent p-4">
        <div className="flex items-start justify-between">
          <div className="text-white">
            {title && <h3 className="text-lg font-semibold">{title}</h3>}
            {description && <p className="text-sm text-neutral-300">{description}</p>}
          </div>
          <button
            onClick={onClose}
            className="rounded-full bg-white/10 p-2 text-white backdrop-blur transition hover:bg-white/20"
            aria-label="Close"
          >
            <XIcon className="h-6 w-6" />
          </button>
        </div>
      </div>

      {/* Main Image Container */}
      <div
        ref={containerRef}
        className="absolute inset-0 flex items-center justify-center overflow-hidden"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
      >
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-white/20 border-t-white" />
          </div>
        )}

        {error ? (
          <div className="text-center text-white">
            <div className="text-6xl mb-4">⚠️</div>
            <p className="text-lg font-medium">Failed to load image</p>
            <p className="text-sm text-neutral-400 mt-2">The image may be corrupted or unavailable</p>
          </div>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            ref={imageRef}
            src={src}
            alt={alt}
            className="max-w-none select-none"
            style={{
              transform: `translate(${position.x}px, ${position.y}px) scale(${zoom})`,
              transition: isDragging ? 'none' : 'transform 0.1s ease-out',
            }}
            draggable={false}
            onLoad={() => setIsLoading(false)}
            onError={() => {
              setIsLoading(false)
              setError(true)
            }}
          />
        )}
      </div>

      {/* Zoom Controls */}
      <div className="absolute bottom-4 left-1/2 z-10 -translate-x-1/2">
        <div className="flex items-center gap-2 rounded-full bg-black/80 px-4 py-2 backdrop-blur">
          <button
            onClick={zoomOut}
            className="rounded-full p-2 text-white transition hover:bg-white/20"
            aria-label="Zoom out"
            disabled={zoom <= MIN_ZOOM}
          >
            <ZoomOutIcon className="h-5 w-5" />
          </button>

          <div className="flex items-center gap-2 px-2">
            <span className="min-w-[60px] text-center text-sm font-medium text-white">
              {Math.round(zoom * 100)}%
            </span>
          </div>

          <button
            onClick={zoomIn}
            className="rounded-full p-2 text-white transition hover:bg-white/20"
            aria-label="Zoom in"
            disabled={zoom >= MAX_ZOOM}
          >
            <ZoomInIcon className="h-5 w-5" />
          </button>

          <div className="mx-2 h-6 w-px bg-white/20" />

          <button
            onClick={fitToScreen}
            className="rounded-full p-2 text-white transition hover:bg-white/20"
            aria-label="Fit to screen"
          >
            <MaximizeIcon className="h-5 w-5" />
          </button>

          <button
            onClick={resetView}
            className="rounded-full p-2 text-white transition hover:bg-white/20"
            aria-label="Reset view"
          >
            <RotateCwIcon className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Annotation */}
      {annotation && (
        <div className="absolute bottom-20 left-1/2 z-10 max-w-md -translate-x-1/2">
          <div className="rounded-lg bg-black/80 px-4 py-2 backdrop-blur">
            <p className="text-sm text-white">{annotation}</p>
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="absolute right-4 top-20 z-10 hidden lg:block">
        <div className="rounded-lg bg-black/60 p-3 text-xs text-white/80 backdrop-blur">
          <p className="font-semibold mb-2">Controls:</p>
          <ul className="space-y-1">
            <li>🖱️ Scroll: Zoom in/out</li>
            <li>🖱️ Drag: Pan image</li>
            <li>⌨️ +/-: Zoom in/out</li>
            <li>⌨️ Arrows: Pan</li>
            <li>⌨️ F: Fit to screen</li>
            <li>⌨️ 0: Reset view</li>
            <li>⌨️ Esc: Close</li>
          </ul>
        </div>
      </div>

      {/* Mobile Instructions */}
      <div className="absolute right-4 top-20 z-10 block lg:hidden">
        <div className="rounded-lg bg-black/60 p-3 text-xs text-white/80 backdrop-blur">
          <p className="font-semibold mb-1">Touch controls:</p>
          <ul className="space-y-1">
            <li>👆 Drag: Pan</li>
            <li>🤏 Pinch: Zoom</li>
          </ul>
        </div>
      </div>
    </div>
  )
}