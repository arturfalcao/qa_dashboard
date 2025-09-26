import Cookies from 'js-cookie'
import { User } from '@qa-dashboard/shared'

export interface AuthUser extends User {
  clientSlug?: string
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
