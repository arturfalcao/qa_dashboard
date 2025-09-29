'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { apiClient } from '@/lib/api'

interface SessionData {
  session: {
    id: string
    startedAt: string
    pausedAt: string | null
    piecesInspected: number
    piecesOk: number
    piecesDefect: number
    piecesPotentialDefect: number
  }
  currentPiece: {
    id: string
    pieceNumber: number
    status: string
    inspectionStartedAt: string
  } | null
  recentPhotos: Array<{
    id: string
    filePath: string
    capturedAt: string
  }>
}

export default function LiveInspectionPage() {
  const params = useParams()
  const router = useRouter()
  const sessionId = params?.sessionId as string

  const [sessionData, setSessionData] = useState<SessionData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isPaused, setIsPaused] = useState(false)

  const loadSessionData = useCallback(async () => {
    if (!sessionId) return

    try {
      const data = await apiClient.getLiveSession(sessionId)
      setSessionData(data)
      setIsPaused(!!data.session.pausedAt)
      if (loading) setLoading(false)
    } catch (err: any) {
      setError(err.message || 'Failed to load session data')
      setLoading(false)
    }
  }, [sessionId, loading])

  // Poll every 5 seconds
  useEffect(() => {
    loadSessionData()
    const interval = setInterval(loadSessionData, 5000)
    return () => clearInterval(interval)
  }, [loadSessionData])

  const handlePause = async () => {
    try {
      await apiClient.pauseInspectionSession(sessionId)
      setIsPaused(true)
      loadSessionData()
    } catch (err: any) {
      alert(err.message || 'Failed to pause session')
    }
  }

  const handleResume = async () => {
    try {
      await apiClient.resumeInspectionSession(sessionId)
      setIsPaused(false)
      loadSessionData()
    } catch (err: any) {
      alert(err.message || 'Failed to resume session')
    }
  }

  const handleEnd = async () => {
    if (!confirm('Are you sure you want to end this inspection session?')) {
      return
    }

    try {
      await apiClient.endInspectionSession(sessionId)
      alert('Session ended successfully!')
      router.push('/operator/inspection')
    } catch (err: any) {
      alert(err.message || 'Failed to end session')
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-primary-600"></div>
      </div>
    )
  }

  if (error || !sessionData) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md p-8 bg-white rounded-2xl shadow-lg text-center">
          <div className="text-red-600">
            <div className="text-6xl mb-4">⚠️</div>
            <p className="text-lg font-semibold">Error</p>
            <p className="text-sm mt-2 text-slate-600">{error || 'Session not found'}</p>
          </div>
          <button
            onClick={() => router.push('/operator/inspection')}
            className="mt-6 px-6 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  const { session, currentPiece, recentPhotos } = sessionData

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header with Status */}
        <div className="bg-white rounded-3xl shadow-xl p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-slate-900">Live Inspection</h1>
                <span
                  className={`px-4 py-1 rounded-full text-sm font-semibold ${
                    isPaused ? 'bg-amber-100 text-amber-800' : 'bg-green-100 text-green-800'
                  }`}
                >
                  {isPaused ? '⏸️ Paused' : '▶️ Active'}
                </span>
              </div>
              <p className="text-slate-600">
                Started: {new Date(session.startedAt).toLocaleTimeString()}
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              {isPaused ? (
                <button
                  onClick={handleResume}
                  className="px-6 py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700 transition shadow-lg"
                >
                  ▶️ Resume
                </button>
              ) : (
                <button
                  onClick={handlePause}
                  className="px-6 py-3 bg-amber-600 text-white rounded-xl font-semibold hover:bg-amber-700 transition shadow-lg"
                >
                  ⏸️ Pause
                </button>
              )}
              <button
                onClick={handleEnd}
                className="px-6 py-3 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 transition shadow-lg"
              >
                ⏹️ End Session
              </button>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="text-4xl font-bold text-primary-600 mb-2">{session.piecesInspected}</div>
            <div className="text-sm font-medium text-slate-600">Pieces Inspected</div>
          </div>
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="text-4xl font-bold text-green-600 mb-2">{session.piecesOk}</div>
            <div className="text-sm font-medium text-slate-600">OK</div>
          </div>
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="text-4xl font-bold text-red-600 mb-2">{session.piecesDefect}</div>
            <div className="text-sm font-medium text-slate-600">Defects</div>
          </div>
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="text-4xl font-bold text-amber-600 mb-2">{session.piecesPotentialDefect}</div>
            <div className="text-sm font-medium text-slate-600">Potential Defects</div>
          </div>
        </div>

        {/* Current Piece */}
        {currentPiece && (
          <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-3xl shadow-xl p-8 mb-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold mb-2">Current Piece</h2>
                <div className="text-5xl font-bold">#{currentPiece.pieceNumber}</div>
                <p className="mt-2 opacity-90">
                  Started: {new Date(currentPiece.inspectionStartedAt).toLocaleTimeString()}
                </p>
              </div>
              <div className="text-6xl">👕</div>
            </div>
          </div>
        )}

        {/* Recent Photos */}
        <div className="bg-white rounded-3xl shadow-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-semibold text-slate-900">Recent Photos</h2>
            <span className="px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-sm font-semibold">
              {recentPhotos.length} photos
            </span>
          </div>

          {recentPhotos.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <div className="text-6xl mb-4">📸</div>
              <p>No photos captured yet</p>
              <p className="text-sm mt-2">Photos will appear here in real-time</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
              {recentPhotos.map((photo) => (
                <div
                  key={photo.id}
                  className="relative aspect-square bg-slate-100 rounded-xl overflow-hidden shadow-md hover:shadow-xl transition group"
                >
                  <img
                    src={`/api/photos/${photo.filePath}`}
                    alt="Inspection photo"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23e2e8f0" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" fill="%2394a3b8" font-size="48"%3E📷%3C/text%3E%3C/svg%3E'
                    }}
                  />
                  <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition flex items-end justify-center pb-2">
                    <span className="text-white text-xs opacity-0 group-hover:opacity-100 transition">
                      {new Date(photo.capturedAt).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Keyboard Shortcuts Guide */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-2xl p-6">
          <h3 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
            <span>⌨️</span>
            Keyboard Shortcuts (Edge Device)
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="bg-white rounded-lg p-3 border border-blue-200">
              <span className="font-bold text-blue-900">Key 1:</span>
              <p className="text-blue-800 mt-1">Take Photo</p>
            </div>
            <div className="bg-white rounded-lg p-3 border border-blue-200">
              <span className="font-bold text-blue-900">Key 2:</span>
              <p className="text-blue-800 mt-1">Flag Defect</p>
            </div>
            <div className="bg-white rounded-lg p-3 border border-blue-200">
              <span className="font-bold text-blue-900">Key 3:</span>
              <p className="text-blue-800 mt-1">Potential Defect</p>
            </div>
            <div className="bg-white rounded-lg p-3 border border-blue-200">
              <span className="font-bold text-blue-900">Key 4:</span>
              <p className="text-blue-800 mt-1">Next Piece</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}