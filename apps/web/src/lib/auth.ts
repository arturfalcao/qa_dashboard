import Cookies from 'js-cookie'
import { User } from '@qa-dashboard/shared'

export interface AuthUser extends User {
  tenantSlug?: string
}

export const getStoredUser = (): AuthUser | null => {
  try {
    const userString = Cookies.get('user')
    return userString ? JSON.parse(userString) : null
  } catch {
    return null
  }
}

export const storeUser = (user: AuthUser): void => {
  Cookies.set('user', JSON.stringify(user), { expires: 7 })
}

export const clearAuth = (): void => {
  Cookies.remove('accessToken')
  Cookies.remove('refreshToken')
  Cookies.remove('user')
}

export const getAccessToken = (): string | null => {
  return Cookies.get('accessToken') || null
}

export const isAuthenticated = (): boolean => {
  return !!getAccessToken() && !!getStoredUser()
}

// Tenant slug mapping (in a real app, this would come from API)
export const getTenantSlug = (tenantId: string): string => {
  // This is a simple mapping - in production, you'd get this from the API
  const tenantMap: Record<string, string> = {
    // These will be populated after seeding
  }
  return tenantMap[tenantId] || 'unknown'
}