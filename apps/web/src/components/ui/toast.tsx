'use client'

import * as React from 'react'
import { createPortal } from 'react-dom'
import { XIcon, CheckCircleIcon, AlertTriangleIcon, InfoIcon } from 'lucide-react'
import { Button } from './button'
import { cn } from '@/lib/utils'

type ToastVariant = 'default' | 'success' | 'warning' | 'danger'

export interface ToastData {
  id: string
  title?: React.ReactNode
  description?: React.ReactNode
  action?: React.ReactNode
  variant?: ToastVariant
  duration?: number
}

interface ToastContextValue {
  toasts: ToastData[]
  publish: (toast: Omit<ToastData, 'id'> & { id?: string }) => void
  dismiss: (id: string) => void
}

const ToastContext = React.createContext<ToastContextValue | undefined>(undefined)

const iconForVariant: Record<ToastVariant, React.ReactNode> = {
  default: <InfoIcon className="h-4 w-4" />, 
  success: <CheckCircleIcon className="h-4 w-4" />, 
  warning: <AlertTriangleIcon className="h-4 w-4" />, 
  danger: <AlertTriangleIcon className="h-4 w-4" />,
}

const variantStyles: Record<ToastVariant, string> = {
  default: 'border-neutral-200 bg-white text-neutral-900',
  success: 'border-success-200 bg-success-50 text-success-700',
  warning: 'border-warning-200 bg-warning-50 text-warning-700',
  danger: 'border-danger-200 bg-danger-50 text-danger-700',
}

const generateId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastData[]>([])
  const timers = React.useRef<Map<string, number>>(new Map())

  const clearTimer = React.useCallback((id: string) => {
    const timeoutId = timers.current.get(id)
    if (timeoutId) {
      window.clearTimeout(timeoutId)
      timers.current.delete(id)
    }
  }, [])

  const dismiss = React.useCallback((id: string) => {
    clearTimer(id)
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }, [clearTimer])

  const publish = React.useCallback<ToastContextValue['publish']>(
    (toast) => {
      const id = toast.id ?? generateId()
      const duration = toast.duration ?? 5000
      const nextToast: ToastData = { ...toast, id, duration }

      setToasts((prev) => [...prev.filter((existing) => existing.id !== id), nextToast])

      clearTimer(id)
      const timeoutId = window.setTimeout(() => dismiss(id), duration)
      timers.current.set(id, timeoutId)
    },
    [clearTimer, dismiss],
  )

  React.useEffect(
    () => () => {
      timers.current.forEach((timeoutId) => window.clearTimeout(timeoutId))
      timers.current.clear()
    },
    [],
  )

  return (
    <ToastContext.Provider value={{ toasts, publish, dismiss }}>
      {children}
      <ToastViewport />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = React.useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

function ToastViewport() {
  const { toasts, dismiss } = useToast()
  const [mounted, setMounted] = React.useState(false)
  const portalRef = React.useRef<HTMLElement | null>(null)

  React.useEffect(() => {
    setMounted(true)
    portalRef.current = document.getElementById('toast-root') || createToastRoot()
  }, [])

  if (!mounted || !portalRef.current) return null

  return createPortal(
    <div className="pointer-events-none fixed inset-x-0 top-4 z-50 flex flex-col items-center gap-3 px-4 sm:items-end sm:px-6">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={() => dismiss(toast.id)} />
      ))}
    </div>,
    portalRef.current,
  )
}

function createToastRoot() {
  const element = document.createElement('div')
  element.setAttribute('id', 'toast-root')
  document.body.appendChild(element)
  return element
}

interface ToastItemProps {
  toast: ToastData
  onDismiss: () => void
}

function ToastItem({ toast, onDismiss }: ToastItemProps) {
  const variant = toast.variant ?? 'default'

  return (
    <div
      role="status"
      className={cn(
        'pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-lg border px-4 py-3 shadow-lg transition-all',
        variantStyles[variant],
      )}
    >
      <span className="mt-0.5 text-current" aria-hidden>
        {iconForVariant[variant]}
      </span>
      <div className="flex-1 text-sm">
        {toast.title && <p className="font-semibold">{toast.title}</p>}
        {toast.description && (
          <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-300">{toast.description}</p>
        )}
        {toast.action && <div className="mt-3">{toast.action}</div>}
      </div>
      <Button
        variant="ghost"
        size="xs"
        className="text-neutral-400 hover:text-neutral-600"
        onClick={onDismiss}
        aria-label="Dismiss notification"
      >
        <XIcon className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}

export type ToastHandle = ReturnType<typeof useToast>
