'use client'

import { Fragment, useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { UserRole, type ClientUser, type Lot } from '@qa-dashboard/shared'
import { useAuth } from '@/components/providers/auth-provider'
import { apiClient } from '@/lib/api'

export default function ClientUsersPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState<ClientUser[]>([])
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [selectedRole, setSelectedRole] = useState<UserRole>(UserRole.CLIENT_VIEWER)
  const [selectedTenantId, setSelectedTenantId] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null)
  const [selectedLotIds, setSelectedLotIds] = useState<string[]>([])
  const [assignmentError, setAssignmentError] = useState<string | null>(null)
  const [assignmentSuccess, setAssignmentSuccess] = useState<string | null>(null)
  const [isSavingAssignments, setIsSavingAssignments] = useState(false)

  const isAdmin = useMemo(() => user?.roles?.includes(UserRole.ADMIN), [user?.roles])

  const availableRoles = useMemo(
    () => [UserRole.CLIENT_VIEWER, UserRole.OPS_MANAGER, UserRole.ADMIN],
    [],
  )

  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: () => apiClient.listTenants(),
    enabled: isAdmin,
  })

  const { data: lots = [], isLoading: lotsLoading } = useQuery<Lot[]>({
    queryKey: ['client-lots'],
    queryFn: () => apiClient.getLots(),
    enabled: Boolean(user?.tenantId),
  })

  const lotNameMap = useMemo(() => new Map(lots.map((lot) => [lot.id, lot.styleRef])), [lots])

  useEffect(() => {
    const fetchUsers = async () => {
      if (!user?.tenantId) {
        return
      }

      try {
        const response = await apiClient.listTenantUsers(user.tenantId)
        setUsers(response)
      } catch (fetchError: any) {
        console.error('Failed to load client users', fetchError)
        setError(fetchError?.message || 'Failed to load users')
      }
    }

    fetchUsers()
  }, [user?.tenantId])

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const targetClientId = isAdmin && selectedTenantId ? selectedTenantId : user?.tenantId

    if (!targetClientId) {
      setError(isAdmin ? 'Please select a client' : 'You must be associated with a client to invite users')
      return
    }

    setError(null)
    setSuccess(null)
    setIsSubmitting(true)

    try {
      const created = await apiClient.createTenantUser(targetClientId, {
        email,
        password,
        roles: [selectedRole],
      })

      setUsers((prev) => [created, ...prev])
      setEmail('')
      setPassword('')
      setSelectedRole(UserRole.CLIENT_VIEWER)
      setSelectedTenantId('')
      setSuccess('New login created successfully')
    } catch (submitError: any) {
      console.error('Failed to create client user', submitError)
      setError(submitError?.message || 'Unable to create login')
    } finally {
      setIsSubmitting(false)
    }
  }

  const openAssignmentPanel = (clientUser: ClientUser) => {
    if (expandedUserId === clientUser.id) {
      setExpandedUserId(null)
      setSelectedLotIds(clientUser.assignedLotIds)
      setAssignmentError(null)
      setAssignmentSuccess(null)
      return
    }

    setExpandedUserId(clientUser.id)
    setSelectedLotIds(clientUser.assignedLotIds)
    setAssignmentError(null)
    setAssignmentSuccess(null)
  }

  const toggleLotSelection = (lotId: string) => {
    setSelectedLotIds((current) =>
      current.includes(lotId)
        ? current.filter((id) => id !== lotId)
        : [...current, lotId],
    )
  }

  const handleAssignmentSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
    clientUser: ClientUser,
  ) => {
    event.preventDefault()

    if (!user?.tenantId) {
      setAssignmentError('You must be associated with a client to update access')
      return
    }

    setAssignmentError(null)
    setAssignmentSuccess(null)
    setIsSavingAssignments(true)

    try {
      const updated = await apiClient.updateTenantUserLots(user.tenantId, clientUser.id, {
        lotIds: selectedLotIds,
      })

      setUsers((prev) => prev.map((entry) => (entry.id === updated.id ? updated : entry)))
      setSelectedLotIds(updated.assignedLotIds)
      setAssignmentSuccess('Lot visibility updated')
    } catch (assignmentErr: any) {
      console.error('Failed to update lot access', assignmentErr)
      setAssignmentError(assignmentErr?.message || 'Unable to update lot access')
    } finally {
      setIsSavingAssignments(false)
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
        <h2 className="text-lg font-medium text-gray-900">Create a new user</h2>
        <p className="mt-1 text-sm text-gray-500">
          {isAdmin
            ? 'Select a client and create login credentials. Set a password that the user can use to log in immediately. No emails are sent.'
            : 'Create login credentials with a password. The user can log in immediately. No emails are sent.'}
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
            {isAdmin && (
              <div className="md:col-span-3">
                <label htmlFor="client" className="block text-sm font-medium text-gray-700">
                  Client
                </label>
                <select
                  id="client"
                  required
                  value={selectedTenantId}
                  onChange={(event) => setSelectedTenantId(event.target.value)}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                >
                  <option value="">Select a client...</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

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
              Password
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
              Set the login password. Share it securely with the user.
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
                  Assigned lots
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((clientUser) => {
                const assignedNames = clientUser.assignedLotIds
                  .map((lotId) => lotNameMap.get(lotId))
                  .filter(Boolean) as string[]
                const isExpanded = expandedUserId === clientUser.id

                return (
                  <Fragment key={clientUser.id}>
                    <tr>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{clientUser.email}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatRoles(clientUser.roles)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {lotsLoading
                          ? 'Loading lots...'
                          : assignedNames.length > 0
                          ? assignedNames.join(', ')
                          : 'No lots assigned'}
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
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          type="button"
                          onClick={() => openAssignmentPanel(clientUser)}
                          className="text-primary-600 hover:text-primary-800"
                        >
                          {expandedUserId === clientUser.id ? 'Close' : 'Manage access'}
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td colSpan={5} className="px-6 py-4 bg-gray-50">
                          <form className="space-y-4" onSubmit={(event) => handleAssignmentSubmit(event, clientUser)}>
                            {assignmentError && (
                              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded">
                                {assignmentError}
                              </div>
                            )}

                            {assignmentSuccess && (
                              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded">
                                {assignmentSuccess}
                              </div>
                            )}

                            <p className="text-sm text-gray-600">
                              Select which lots this user can see when they sign in.
                            </p>

                            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                              {lotsLoading ? (
                                <div className="sm:col-span-2 lg:col-span-3 text-sm text-gray-500">
                                  Loading lots...
                                </div>
                              ) : lots.length === 0 ? (
                                <div className="sm:col-span-2 lg:col-span-3 text-sm text-gray-500">
                                  No lots available yet.
                                </div>
                              ) : (
                                lots
                                  .slice()
                                  .sort((a, b) => a.styleRef.localeCompare(b.styleRef))
                                  .map((lot) => (
                                    <label key={lot.id} className="flex items-start space-x-2 text-sm text-gray-700">
                                      <input
                                        type="checkbox"
                                        checked={selectedLotIds.includes(lot.id)}
                                        onChange={() => toggleLotSelection(lot.id)}
                                        className="mt-1 h-4 w-4 text-primary-600 border-gray-300 rounded"
                                      />
                                      <span>
                                        <span className="font-medium text-gray-900">{lot.styleRef}</span>
                                        {lot.factory?.name && (
                                          <span className="block text-xs text-gray-500">
                                            {lot.factory.name}
                                          </span>
                                        )}
                                      </span>
                                    </label>
                                  ))
                              )}
                            </div>

                            <div className="flex items-center justify-between">
                              <button
                                type="button"
                                className="text-sm text-gray-500 hover:text-gray-700"
                                onClick={() => setSelectedLotIds([])}
                                disabled={isSavingAssignments}
                              >
                                Clear selection
                              </button>

                              <button
                                type="submit"
                                disabled={isSavingAssignments}
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                              >
                                {isSavingAssignments ? 'Saving...' : 'Save access'}
                              </button>
                            </div>
                          </form>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}

              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-6 text-center text-sm text-gray-500">
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
