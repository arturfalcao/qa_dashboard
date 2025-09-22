'use client'

import Link from 'next/link'
import { useParams, usePathname } from 'next/navigation'
import {
  ActivityIcon,
  PackageIcon,
  BarChart3Icon,
  DownloadIcon,
  PlayCircleIcon,
  PauseCircleIcon,
  ArrowRightCircleIcon
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'

const navigation = [
  { name: 'Live Feed', href: '/feed', icon: ActivityIcon },
  { name: 'Batches', href: '/batches', icon: PackageIcon },
  { name: 'Process Tracking', href: '/process', icon: ArrowRightCircleIcon },
  { name: 'Analytics', href: '/analytics', icon: BarChart3Icon },
  { name: 'Exports', href: '/exports', icon: DownloadIcon },
]

export function Sidebar() {
  const params = useParams()
  const pathname = usePathname()
  const queryClient = useQueryClient()
  
  const tenantSlug = params.tenantSlug as string
  const basePath = `/t/${tenantSlug}`

  const { data: generatorStatus } = useQuery({
    queryKey: ['mock-generator-status'],
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3001'}/mock/inspections/status`)
      return response.json()
    },
    refetchInterval: 5000,
  })

  const startGeneratorMutation = useMutation({
    mutationFn: () => apiClient.startMockGenerator(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mock-generator-status'] })
    },
  })

  const stopGeneratorMutation = useMutation({
    mutationFn: () => apiClient.stopMockGenerator(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mock-generator-status'] })
    },
  })

  const isGeneratorRunning = generatorStatus?.isRunning

  return (
    <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-sm border-r border-gray-200 pt-16">
      <div className="flex flex-col h-full">
        <div className="flex-1 px-4 py-6">
          <nav className="space-y-1">
            {navigation.map((item) => {
              const href = `${basePath}${item.href}`
              const isActive = pathname === href
              
              return (
                <Link
                  key={item.name}
                  href={href}
                  className={cn(
                    'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors',
                    isActive
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                >
                  <item.icon
                    className={cn(
                      'mr-3 h-5 w-5 transition-colors',
                      isActive
                        ? 'text-primary-500'
                        : 'text-gray-400 group-hover:text-gray-500'
                    )}
                  />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </div>

        <div className="px-4 py-4 border-t border-gray-200">
          <div className="space-y-2">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Mock Generator
            </div>
            <button
              onClick={() => {
                if (isGeneratorRunning) {
                  stopGeneratorMutation.mutate()
                } else {
                  startGeneratorMutation.mutate()
                }
              }}
              disabled={startGeneratorMutation.isPending || stopGeneratorMutation.isPending}
              className={cn(
                'w-full flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors',
                isGeneratorRunning
                  ? 'bg-red-50 text-red-700 hover:bg-red-100'
                  : 'bg-green-50 text-green-700 hover:bg-green-100'
              )}
            >
              {isGeneratorRunning ? (
                <PauseCircleIcon className="mr-2 h-4 w-4" />
              ) : (
                <PlayCircleIcon className="mr-2 h-4 w-4" />
              )}
              {isGeneratorRunning ? 'Stop' : 'Start'} Mock Data
            </button>
            
            <div className="text-xs text-gray-500">
              Status: {isGeneratorRunning ? 'Running' : 'Stopped'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}