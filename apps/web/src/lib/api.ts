import Cookies from 'js-cookie'
import {
  LoginDto,
  AuthResponse,
  Inspection,
  Event,
  Lot,
  Factory,
  DefectRateAnalytics,
  ThroughputAnalytics,
  DefectTypeAnalytics,
  ApprovalTimeAnalytics,
  ExportQuery,
  LotStatus,
  SupplyChainRole,
  LotSupplierRole,
  OperatorDevice,
  OperatorDeviceDetail,
  OperatorLotSummary,
  OperatorLotFeedItem,
  OperatorCommandResult,
  OperatorAssignLotPayload,
  OperatorReprintPayload,
  OperatorFlagPayload,
  Client,
  ClientUser,
  CreateClientUserDto,
  UpdateClientUserLotsDto,
} from '@qa-dashboard/shared'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3001'

class ApiClient {
  private getAuthHeader(): Record<string, string> {
    const token = Cookies.get('accessToken')
    console.log('🍪 API Client - Token from cookies:', token ? `${token.slice(0, 20)}...` : 'null')
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

    Cookies.set('accessToken', response.accessToken, { expires: 1 / 24 })
    Cookies.set('refreshToken', response.refreshToken, { expires: 7 })

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

    Cookies.set('accessToken', response.accessToken, { expires: 1 / 24 })
    return response
  }

  // Tenants
  async getTenantById(tenantId: string): Promise<Client> {
    return this.request<Client>(`/tenants/${tenantId}`)
  }

  async listTenants() {
    return this.request<Array<{ id: string; name: string; slug: string; logoUrl?: string }>>('/tenants')
  }

  // Clients
  async listClients(): Promise<Client[]> {
    return this.request<Client[]>('/clients')
  }

  async listTenantUsers(tenantId: string): Promise<ClientUser[]> {
    return this.request<ClientUser[]>(`/tenants/${tenantId}/users`)
  }

  async createTenantUser(
    tenantId: string,
    payload: CreateClientUserDto,
  ): Promise<ClientUser> {
    return this.request<ClientUser>(`/tenants/${tenantId}/users`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async updateTenantUserLots(
    tenantId: string,
    userId: string,
    payload: UpdateClientUserLotsDto,
  ): Promise<ClientUser> {
    return this.request<ClientUser>(`/tenants/${tenantId}/users/${userId}/lots`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }

  // Operator endpoints
  async getOperatorDevices(site?: string): Promise<OperatorDevice[]> {
    const query = site ? `?site=${encodeURIComponent(site)}` : ''
    return this.request<OperatorDevice[]>(`/operator/devices${query}`)
  }

  async getOperatorDevice(deviceId: string): Promise<OperatorDeviceDetail> {
    return this.request<OperatorDeviceDetail>(`/operator/devices/${deviceId}`)
  }

  async assignOperatorDevice(
    deviceId: string,
    payload: OperatorAssignLotPayload,
  ): Promise<OperatorDeviceDetail> {
    return this.request<OperatorDeviceDetail>(`/operator/devices/${deviceId}/assign`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async issueReprintCommand(
    deviceId: string,
    payload: OperatorReprintPayload,
  ): Promise<OperatorCommandResult> {
    return this.request<OperatorCommandResult>(`/operator/devices/${deviceId}/commands/reprint`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async getOperatorActiveLots(site?: string): Promise<OperatorLotSummary[]> {
    const query = site ? `?site=${encodeURIComponent(site)}` : ''
    return this.request<OperatorLotSummary[]>(`/operator/lots/active${query}`)
  }

  async getOperatorLotFeed(lotId: string, site?: string): Promise<OperatorLotFeedItem[]> {
    const query = site ? `?site=${encodeURIComponent(site)}` : ''
    return this.request<OperatorLotFeedItem[]>(`/operator/lots/${lotId}/feed${query}`)
  }

  async createOperatorFlag(
    lotId: string,
    payload: OperatorFlagPayload,
  ): Promise<OperatorLotFeedItem> {
    return this.request<OperatorLotFeedItem>(`/operator/lots/${lotId}/flags`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  // Inspections
  async getInspections(since?: string, limit?: number): Promise<Inspection[]> {
    const params = new URLSearchParams()
    if (since) params.append('since', since)
    if (limit) params.append('limit', limit.toString())

    return this.request<Inspection[]>(`/inspections?${params.toString()}`)
  }

  async addDefect(
    inspectionId: string,
    payload: {
      pieceCode?: string
      note?: string
      defectTypeId?: string
      photos?: Array<{
        url: string
        annotation?: Record<string, any>
      }>
    }
  ): Promise<any> {
    return this.request(`/inspections/${inspectionId}/defects`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  // Events
  async getEvents(since?: string, limit?: number): Promise<Event[]> {
    const params = new URLSearchParams()
    if (since) params.append('since', since)
    if (limit) params.append('limit', limit.toString())

    return this.request<Event[]>(`/events?${params.toString()}`)
  }

  // Lots
  async getLots(): Promise<Lot[]> {
    return this.request<Lot[]>('/lots')
  }

  async getLot(id: string): Promise<Lot> {
    return this.request<Lot>(`/lots/${id}`)
  }

  async createLot(payload: {
    tenantId?: string
    suppliers: Array<{
      factoryId: string
      stage?: string | null
      isPrimary?: boolean
      roles?: Array<Pick<LotSupplierRole, 'roleId' | 'sequence' | 'co2Kg' | 'notes'>>
    }>
    styleRef: string
    quantityTotal: number
    status?: LotStatus
    factoryId?: string
  }): Promise<Lot> {
    return this.request<Lot>('/lots', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async updateLot(
    id: string,
    payload: Partial<{
      suppliers: Array<{
        factoryId: string
        stage?: string | null
        isPrimary?: boolean
        roles?: Array<Pick<LotSupplierRole, 'roleId' | 'sequence' | 'co2Kg' | 'notes'>>
      }>
      factoryId: string
      styleRef: string
      quantityTotal: number
      status: LotStatus
    }>,
  ): Promise<Lot> {
    return this.request<Lot>(`/lots/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  }

  async advanceLotSupplyChain(id: string): Promise<Lot> {
    return this.request<Lot>(`/lots/${id}/supply-chain/advance`, {
      method: 'POST',
    })
  }

  async approveLot(id: string, note?: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/lots/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    })
  }

  async rejectLot(id: string, note: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/lots/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    })
  }

  // Photos & annotations (best-effort placeholder implementations)
  async getPhotosForInspection(inspectionId: string): Promise<Array<{ id: string; url: string; angle?: string }>> {
    try {
      return await this.request<Array<{ id: string; url: string; angle?: string }>>(
        `/inspections/${inspectionId}/photos`,
      )
    } catch {
      return []
    }
  }

  async getAnnotationsForPhoto(photoId: string): Promise<Array<{ id: string; x: number; y: number; comment?: string; defectType?: string; severity?: string }>> {
    try {
      return await this.request<Array<{ id: string; x: number; y: number; comment?: string; defectType?: string; severity?: string }>>(
        `/photos/${photoId}/annotations`,
      )
    } catch {
      return []
    }
  }

  async createAnnotation(
    photoId: string,
    x: number,
    y: number,
    comment: string,
    defectType?: string,
    severity?: string,
  ): Promise<{ id: string; x: number; y: number; comment?: string; defectType?: string; severity?: string }> {
    return this.request<{ id: string; x: number; y: number; comment?: string; defectType?: string; severity?: string }>(`/photos/${photoId}/annotations`, {
      method: 'POST',
      body: JSON.stringify({ x, y, comment, defectType, severity }),
    })
  }

  async deleteAnnotation(annotationId: string): Promise<void> {
    await this.request(`/annotations/${annotationId}`, {
      method: 'DELETE',
    })
  }

  // Factories
  async getFactories(): Promise<Factory[]> {
    return this.request<Factory[]>('/factories')
  }

  async createFactory(payload: {
    name: string
    city?: string
    country?: string
    capabilities?: Array<{ roleId: string; co2OverrideKg?: number | null; notes?: string | null }>
    certifications?: Array<{ certification: string }>
  }): Promise<Factory> {
    return this.request<Factory>('/factories', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async updateFactory(
    id: string,
    payload: {
      name?: string
      city?: string
      country?: string
      capabilities?: Array<{ roleId: string; co2OverrideKg?: number | null; notes?: string | null }>
      certifications?: Array<{ certification: string }>
    },
  ): Promise<Factory> {
    return this.request<Factory>(`/factories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  }

  async getSupplyChainRoles(): Promise<SupplyChainRole[]> {
    return this.request<SupplyChainRole[]>('/supply-chain/roles')
  }

  // Analytics
  async getDefectRate(
    groupBy?: 'style' | 'factory',
    range?: 'last_7d' | 'last_30d',
  ): Promise<DefectRateAnalytics> {
    const params = new URLSearchParams()
    if (groupBy) params.append('groupBy', groupBy)
    if (range) params.append('range', range)

    return this.request<DefectRateAnalytics>(`/analytics/defect-rate?${params.toString()}`)
  }

  async getThroughput(
    bucket?: 'day' | 'week',
    range?: 'last_7d' | 'last_30d',
  ): Promise<ThroughputAnalytics> {
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
  async generatePDF(query: ExportQuery): Promise<{ downloadUrl: string }> {
    return this.request<{ downloadUrl: string }>('/exports/pdf', {
      method: 'POST',
      body: JSON.stringify(query),
    })
  }

  async generateCSV(query: ExportQuery): Promise<{ downloadUrl: string }> {
    return this.request<{ downloadUrl: string }>('/exports/csv', {
      method: 'POST',
      body: JSON.stringify(query),
    })
  }

  // Reports
  async getReports(type?: string): Promise<any[]> {
    const params = new URLSearchParams()
    if (type) params.append('type', type)
    return this.request<any[]>(`/reports?${params.toString()}`)
  }

  async getReport(id: string): Promise<any> {
    return this.request<any>(`/reports/${id}`)
  }

  async downloadReport(id: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/reports/${id}/download`, {
      headers: {
        ...this.getAuthHeader(),
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to download report: ${response.statusText}`)
    }

    return response.blob()
  }

  async generateExecutiveSummary(params: any, language = 'EN'): Promise<any> {
    return this.request<any>(`/reports/executive-summary?language=${language}`, {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }

  async generateLotInspectionReport(lotId: string, params: any = {}, language = 'EN'): Promise<any> {
    return this.request<any>(`/reports/lot-inspection/${lotId}?language=${language}`, {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }

  async generateMeasurementComplianceSheet(lotId: string, params: any = {}, language = 'EN'): Promise<any> {
    return this.request<any>(`/reports/measurement-compliance/${lotId}?language=${language}`, {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }

  async generatePackagingReadinessReport(lotId: string, params: any = {}, language = 'EN'): Promise<any> {
    return this.request<any>(`/reports/packaging-readiness/${lotId}?language=${language}`, {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }

  async generateSupplierPerformanceSnapshot(params: any, language = 'EN'): Promise<any> {
    return this.request<any>(`/reports/supplier-performance?language=${language}`, {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }

  async generateInlineQcCheckpoints(lotId: string, params: any = {}, language = 'EN'): Promise<any> {
    return this.request<any>(`/reports/inline-qc/${lotId}?language=${language}`, {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }

  async generateDppSummary(params: any, language = 'EN'): Promise<any> {
    return this.request<any>(`/reports/dpp-summary?language=${language}`, {
      method: 'POST',
      body: JSON.stringify(params),
    })
  }

  async generateGenericReport(request: any): Promise<any> {
    return this.request<any>('/reports/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  // DPP
  async getPublicDpp(id: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/dpp/${id}.json`)
    if (!response.ok) {
      throw new Error(`DPP not found: ${response.status}`)
    }
    return response.json()
  }

  // Admin
  async seedData(): Promise<any> {
    return this.request('/admin/seed', { method: 'POST' })
  }
}

export const apiClient = new ApiClient()
