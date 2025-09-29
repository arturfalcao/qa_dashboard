'use client'

import { useAuth } from '@/components/providers/auth-provider'
import { useParams } from 'next/navigation'
import { ChevronDownIcon, UserIcon } from 'lucide-react'
import { useState } from 'react'

export function Navbar() {
  const { user, logout } = useAuth()
  const params = useParams()
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)

  const clientSlug = params.clientSlug as string
  const clientName = user?.clientName || clientSlug

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200 fixed w-full z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <div className="flex-shrink-0 flex items-center">
              <h1 className="text-xl font-bold text-gray-900">
                QA Dashboard
              </h1>
              {clientName && (
                <span className="ml-3 px-2 py-1 text-xs font-medium bg-primary-100 text-primary-800 rounded">
                  {clientName}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="relative">
              <button
                type="button"
                className="flex items-center text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              >
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                    <UserIcon className="w-5 h-5 text-gray-600" />
                  </div>
                  <span className="text-gray-700">{user?.email}</span>
                  <ChevronDownIcon className="w-4 h-4 text-gray-500" />
                </div>
              </button>

              {isDropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50">
                  {user?.roles?.length && (
                    <div className="px-4 py-2 text-sm text-gray-500 border-b">
                      Roles: {user.roles.map((role) => role.replace('_', ' ')).join(', ')}
                    </div>
                  )}
                  <button
                    onClick={logout}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}
