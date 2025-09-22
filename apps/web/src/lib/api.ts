import Cookies from 'js-cookie'
import {
  LoginDto,
  AuthResponse,
  Inspection,
  Event,
  Batch,
  DefectRateAnalytics,
  ThroughputAnalytics,
  DefectTypeAnalytics,
  ApprovalTimeAnalytics,
  InspectionPhoto,
  PhotoAnnotation,
  PhotoAngle,
  DefectType,
  DefectSeverity
} from '@qa-dashboard/shared'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3001'

class ApiClient {
  private getAuthHeader(): Record<string, string> {
    const token = Cookies.get('accessToken')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeader(),
        ...(options.headers as Record<string, string> || {}),
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Network error' }))
      throw new Error(error.message || `HTTP ${response.status}`)
    }

    return response.json()
  }

  // Auth
  async login(credentials: LoginDto): Promise<AuthResponse> {
    const response = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    })
    
    // Store tokens in cookies
    Cookies.set('accessToken', response.accessToken, { expires: 1/24 }) // 1 hour
    Cookies.set('refreshToken', response.refreshToken, { expires: 7 }) // 7 days
    
    return response
  }

  async logout(): Promise<void> {
    try {
      await this.request('/auth/logout', { method: 'POST' })
    } finally {
      Cookies.remove('accessToken')
      Cookies.remove('refreshToken')
    }
  }

  async refreshToken(): Promise<{ accessToken: string }> {
    const refreshToken = Cookies.get('refreshToken')
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    const response = await this.request<{ accessToken: string }>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refreshToken }),
    })

    Cookies.set('accessToken', response.accessToken, { expires: 1/24 })
    return response
  }

  // Inspections
  async getInspections(since?: string, limit?: number): Promise<Inspection[]> {
    const params = new URLSearchParams()
    if (since) params.append('since', since)
    if (limit) params.append('limit', limit.toString())
    
    return this.request<Inspection[]>(`/inspections?${params.toString()}`)
  }

  // Events
  async getEvents(since?: string, limit?: number): Promise<Event[]> {
    const params = new URLSearchParams()
    if (since) params.append('since', since)
    if (limit) params.append('limit', limit.toString())
    
    return this.request<Event[]>(`/events?${params.toString()}`)
  }

  // Batches
  async getBatches(): Promise<Batch[]> {
    return this.request<Batch[]>('/batches')
  }

  async getBatch(id: string): Promise<Batch> {
    return this.request<Batch>(`/batches/${id}`)
  }

  async approveBatch(id: string, comment?: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/batches/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ comment }),
    })
  }

  async rejectBatch(id: string, comment: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/batches/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ comment }),
    })
  }

  // Analytics
  async getDefectRate(groupBy?: 'style' | 'vendor', range?: 'last_7d' | 'last_30d'): Promise<DefectRateAnalytics> {
    const params = new URLSearchParams()
    if (groupBy) params.append('groupBy', groupBy)
    if (range) params.append('range', range)
    
    return this.request<DefectRateAnalytics>(`/analytics/defect-rate?${params.toString()}`)
  }

  async getThroughput(bucket?: 'day' | 'week', range?: 'last_7d' | 'last_30d'): Promise<ThroughputAnalytics> {
    const params = new URLSearchParams()
    if (bucket) params.append('bucket', bucket)
    if (range) params.append('range', range)
    
    return this.request<ThroughputAnalytics>(`/analytics/throughput?${params.toString()}`)
  }

  async getDefectTypes(range?: 'last_7d' | 'last_30d'): Promise<DefectTypeAnalytics> {
    const params = new URLSearchParams()
    if (range) params.append('range', range)
    
    return this.request<DefectTypeAnalytics>(`/analytics/defect-types?${params.toString()}`)
  }

  async getApprovalTime(range?: 'last_7d' | 'last_30d'): Promise<ApprovalTimeAnalytics> {
    const params = new URLSearchParams()
    if (range) params.append('range', range)
    
    return this.request<ApprovalTimeAnalytics>(`/analytics/approval-time?${params.toString()}`)
  }

  // Exports
  async generatePDF(batchId?: string, range?: 'last_7d' | 'last_30d'): Promise<{ downloadUrl: string }> {
    return this.request<{ downloadUrl: string }>('/exports/pdf', {
      method: 'POST',
      body: JSON.stringify({ batchId, range }),
    })
  }

  async generateCSV(range?: 'last_7d' | 'last_30d'): Promise<{ downloadUrl: string }> {
    return this.request<{ downloadUrl: string }>('/exports/csv', {
      method: 'POST',
      body: JSON.stringify({ range }),
    })
  }

  // Admin/Mock
  async seedData(): Promise<any> {
    return this.request('/admin/seed', { method: 'POST' })
  }

  async startMockGenerator(): Promise<{ message: string }> {
    return this.request('/mock/inspections/start', { method: 'POST' })
  }

  async stopMockGenerator(): Promise<{ message: string }> {
    return this.request('/mock/inspections/stop', { method: 'POST' })
  }

  // Enhanced Photo Management
  async uploadInspectionPhoto(file: File, inspectionId: string, angle: PhotoAngle): Promise<InspectionPhoto> {
    const formData = new FormData()
    formData.append('photo', file)
    formData.append('inspectionId', inspectionId)
    formData.append('angle', angle)

    const response = await fetch(`${API_BASE_URL}/inspection-photos/upload`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
      },
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Upload failed' }))
      throw new Error(error.message || `HTTP ${response.status}`)
    }

    return response.json()
  }

  async getPhotosForInspection(inspectionId: string): Promise<InspectionPhoto[]> {
    return this.request<InspectionPhoto[]>(`/inspection-photos/inspection/${inspectionId}`)
  }

  async getPhotosByAngle(inspectionId: string, angle: PhotoAngle): Promise<InspectionPhoto[]> {
    return this.request<InspectionPhoto[]>(`/inspection-photos/inspection/${inspectionId}/angle?angle=${angle}`)
  }

  async getPhoto(photoId: string): Promise<InspectionPhoto> {
    return this.request<InspectionPhoto>(`/inspection-photos/${photoId}`)
  }

  async deletePhoto(photoId: string): Promise<void> {
    return this.request(`/inspection-photos/${photoId}`, { method: 'DELETE' })
  }

  // Photo Annotations
  async createAnnotation(
    photoId: string,
    x: number,
    y: number,
    comment: string,
    defectType?: DefectType,
    defectSeverity?: DefectSeverity
  ): Promise<PhotoAnnotation> {
    return this.request<PhotoAnnotation>('/photo-annotations', {
      method: 'POST',
      body: JSON.stringify({
        photoId,
        x,
        y,
        comment,
        defectType,
        defectSeverity,
      }),
    })
  }

  async getAnnotationsForPhoto(photoId: string): Promise<PhotoAnnotation[]> {
    return this.request<PhotoAnnotation[]>(`/photo-annotations/photo/${photoId}`)
  }

  async updateAnnotation(
    annotationId: string,
    updates: {
      x?: number
      y?: number
      comment?: string
      defectType?: DefectType
      defectSeverity?: DefectSeverity
    }
  ): Promise<PhotoAnnotation> {
    return this.request<PhotoAnnotation>(`/photo-annotations/${annotationId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    })
  }

  async deleteAnnotation(annotationId: string): Promise<void> {
    return this.request(`/photo-annotations/${annotationId}`, { method: 'DELETE' })
  }
}

export const apiClient = new ApiClient()