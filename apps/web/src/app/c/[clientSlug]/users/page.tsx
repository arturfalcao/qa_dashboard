'use client'

import { useEffect, useMemo, useState } from 'react'
import { UserRole, type ClientUser } from '@qa-dashboard/shared'
import { useAuth } from '@/components/providers/auth-provider'
import { apiClient } from '@/lib/api'

export default function ClientUsersPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState<ClientUser[]>([])
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [selectedRole, setSelectedRole] = useState<UserRole>(UserRole.CLIENT_VIEWER)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const availableRoles = useMemo(
    () => [UserRole.CLIENT_VIEWER, UserRole.OPS_MANAGER, UserRole.ADMIN],
    [],
  )

  useEffect(() => {
    const fetchUsers = async () => {
      if (!user?.clientId) {
        return
      }

      try {
        const response = await apiClient.listClientUsers(user.clientId)
        setUsers(response)
      } catch (fetchError: any) {
        console.error('Failed to load client users', fetchError)
        setError(fetchError?.message || 'Failed to load users')
      }
    }

    fetchUsers()
  }, [user?.clientId])

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!user?.clientId) {
      setError('You must be associated with a client to invite users')
      return
    }

    setError(null)
    setSuccess(null)
    setIsSubmitting(true)

    try {
      const created = await apiClient.createClientUser(user.clientId, {
        email,
        password,
        roles: [selectedRole],
      })

      setUsers((prev) => [created, ...prev])
      setEmail('')
      setPassword('')
      setSelectedRole(UserRole.CLIENT_VIEWER)
      setSuccess('New login created successfully')
    } catch (submitError: any) {
      console.error('Failed to create client user', submitError)
      setError(submitError?.message || 'Unable to create login')
    } finally {
      setIsSubmitting(false)
    }
  }

  const formatRoles = (roles: UserRole[]) =>
    roles
      .map((role) => role.replace(/_/g, ' ').toLowerCase())
      .map((role) => role.charAt(0).toUpperCase() + role.slice(1))
      .join(', ')

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Client Access</h1>
        <p className="mt-2 text-sm text-gray-600">
          Create logins for partners and clients so they can sign in and review their lot status.
        </p>
      </div>

      <div className="bg-white shadow-sm rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-900">Invite a new user</h2>
        <p className="mt-1 text-sm text-gray-500">
          Passwords must be at least eight characters. New accounts are active immediately and receive the selected role.
        </p>

        <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded">
              {error}
            </div>
          )}

          {success && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded">
              {success}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                placeholder="client@example.com"
              />
            </div>

            <div>
              <label htmlFor="role" className="block text-sm font-medium text-gray-700">
                Role
              </label>
              <select
                id="role"
                value={selectedRole}
                onChange={(event) => setSelectedRole(event.target.value as UserRole)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              >
                {availableRoles.map((role) => (
                  <option key={role} value={role}>
                    {role.replace(/_/g, ' ').toLowerCase().replace(/(^|\s)\S/g, (match) => match.toUpperCase())}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="md:w-1/2">
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Temporary password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              placeholder="At least 8 characters"
            />
            <p className="mt-1 text-xs text-gray-500">
              Share the password securely with the invitee. They will be able to log in right away.
            </p>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            {isSubmitting ? 'Creating...' : 'Create login'}
          </button>
        </form>
      </div>

      <div className="bg-white shadow-sm rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Active users</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Roles
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((clientUser) => (
                <tr key={clientUser.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{clientUser.email}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatRoles(clientUser.roles)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium ${
                        clientUser.isActive
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {clientUser.isActive ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))}

              {users.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-6 py-6 text-center text-sm text-gray-500">
                    No users yet. Invite your first client contact above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
