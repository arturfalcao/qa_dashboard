'use client'

import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { UserRole, type ClientUser, type Lot } from '@qa-dashboard/shared'
import { useAuth } from '@/components/providers/auth-provider'
import { apiClient } from '@/lib/api'
import { PageHeader } from '@/components/ui/page-header'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectOption } from '@/components/ui/select'
import { EmptyState } from '@/components/ui/empty-state'
import { BadgeCheckIcon, UsersIcon } from 'lucide-react'
import { useToast } from '@/components/ui/toast'
import { cn } from '@/lib/utils'

export default function ClientUsersPage() {
  const { user } = useAuth()
  const { publish } = useToast()

  const [users, setUsers] = useState<ClientUser[]>([])
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [selectedRole, setSelectedRole] = useState<UserRole>(UserRole.CLIENT_VIEWER)
  const [selectedTenantId, setSelectedTenantId] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null)
  const [selectedLotIds, setSelectedLotIds] = useState<string[]>([])
  const [isSavingAssignments, setIsSavingAssignments] = useState(false)

  const isAdmin = useMemo(() => user?.roles?.includes(UserRole.ADMIN), [user?.roles])

  const availableRoles = useMemo<SelectOption<UserRole>[]>(
    () => [
      { value: UserRole.CLIENT_VIEWER, label: 'Viewer' },
      { value: UserRole.OPS_MANAGER, label: 'Operations Manager' },
      { value: UserRole.ADMIN, label: 'Administrator' },
    ],
    [],
  )

  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: () => apiClient.listTenants(),
    enabled: isAdmin,
  })

  const tenantOptions = useMemo<SelectOption<string>[]>(
    () => clients.map((client) => ({ value: client.id, label: client.name })),
    [clients],
  )

  const { data: lots = [], isLoading: lotsLoading } = useQuery<Lot[]>({
    queryKey: ['client-lots'],
    queryFn: () => apiClient.getLots(),
    enabled: Boolean(user?.tenantId),
  })

  useEffect(() => {
    const fetchUsers = async () => {
      if (!user?.tenantId) {
        return
      }
      try {
        const response = await apiClient.listTenantUsers(user.tenantId)
        setUsers(response)
      } catch (fetchError: any) {
        publish({
          variant: 'danger',
          title: 'Failed to load users',
          description: fetchError?.message || 'Unable to fetch client users.',
        })
      }
    }

    fetchUsers()
  }, [publish, user?.tenantId])

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const targetClientId = isAdmin && selectedTenantId ? selectedTenantId : user?.tenantId

    if (!targetClientId) {
      publish({
        variant: 'danger',
        title: isAdmin ? 'Select a tenant' : 'Tenant required',
        description: isAdmin
          ? 'Choose which client should receive the new login.'
          : 'You must be associated with a client to invite users.',
      })
      return
    }

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
      publish({ variant: 'success', title: 'Access granted', description: 'New login created successfully.' })
    } catch (submitError: any) {
      publish({
        variant: 'danger',
        title: 'Unable to create login',
        description: submitError?.message || 'Please try again later.',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const openAssignmentPanel = (clientUser: ClientUser) => {
    if (expandedUserId === clientUser.id) {
      setExpandedUserId(null)
      setSelectedLotIds([])
      return
    }

    setExpandedUserId(clientUser.id)
    setSelectedLotIds(clientUser.assignedLotIds)
  }

  const toggleLotSelection = (lotId: string) => {
    setSelectedLotIds((current) => (current.includes(lotId) ? current.filter((id) => id !== lotId) : [...current, lotId]))
  }

  const handleAssignmentSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
    clientUser: ClientUser,
  ) => {
    event.preventDefault()

    if (!user?.tenantId) {
      publish({ variant: 'danger', title: 'Tenant required', description: 'Cannot update access without a tenant context.' })
      return
    }

    setIsSavingAssignments(true)
    try {
      const updated = await apiClient.updateTenantUserLots(user.tenantId, clientUser.id, {
        lotIds: selectedLotIds,
      })

      setUsers((prev) => prev.map((entry) => (entry.id === updated.id ? updated : entry)))
      setSelectedLotIds(updated.assignedLotIds)
      publish({ variant: 'success', title: 'Visibility updated' })
    } catch (assignmentErr: any) {
      publish({
        variant: 'danger',
        title: 'Unable to update access',
        description: assignmentErr?.message || 'Try again shortly.',
      })
    } finally {
      setIsSavingAssignments(false)
    }
  }

  const formatRoles = (roles: UserRole[]) =>
    roles
      .map((role) => role.replace(/_/g, ' ').toLowerCase())
      .map((role) => role.charAt(0).toUpperCase() + role.slice(1))
      .join(', ')

  const activeUsers = users.length

  return (
    <div className="space-y-8">
      <PageHeader
        title="User access"
        description="Invite stakeholders and control lot-level visibility."
        actions={
          <Button onClick={() => document.getElementById('invite-user-name')?.scrollIntoView({ behavior: 'smooth' })}>
            Invite user
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Total users</CardDescription>
            <CardTitle>{activeUsers}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Administrators</CardDescription>
            <CardTitle>{users.filter((entry) => entry.roles.includes(UserRole.ADMIN)).length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Lot reviewers</CardDescription>
            <CardTitle>{users.filter((entry) => entry.roles.includes(UserRole.OPS_MANAGER)).length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Viewer licences</CardDescription>
            <CardTitle>{users.filter((entry) => entry.roles.includes(UserRole.CLIENT_VIEWER)).length}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Invite a new user</CardTitle>
          <CardDescription>Create credentials and assign a default role.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-2" id="invite-user-name">
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700" htmlFor="invite-email">
                Email address
              </label>
              <Input
                id="invite-email"
                type="email"
                name="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                placeholder="jessica@brand.com"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700" htmlFor="invite-password">
                Temporary password
              </label>
              <Input
                id="invite-password"
                type="text"
                name="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                placeholder="Provide a secure starter password"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700">Role</label>
              <Select
                value={selectedRole}
                onChange={(value) => setSelectedRole(value as UserRole)}
                options={availableRoles}
              />
            </div>
            {isAdmin && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-neutral-700">Assign to tenant</label>
                <Select
                  value={selectedTenantId}
                  onChange={(value) => setSelectedTenantId(value as string)}
                  options={tenantOptions}
                />
              </div>
            )}
            <div className="md:col-span-2 flex justify-end">
              <Button type="submit" loading={isSubmitting}>
                Create login
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <CardTitle>Existing users</CardTitle>
            <CardDescription>Manage credentials and lot access for each user.</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {users.length === 0 ? (
            <EmptyState
              icon={<UsersIcon className="h-5 w-5" />}
              title="No users enrolled"
              description="Invite your team to collaborate on inspections and approvals."
              action={{ label: 'Invite user', onClick: () => document.getElementById('invite-user-name')?.scrollIntoView({ behavior: 'smooth' }) }}
            />
          ) : (
            users.map((clientUser) => (
              <Card key={clientUser.id} className="border-neutral-200">
                <CardContent className="space-y-4 p-5">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                        {clientUser.email}
                      </p>
                      <p className="text-xs text-neutral-500">Roles: {formatRoles(clientUser.roles)}</p>
                      <p className="text-xs text-neutral-500">
                        Lots assigned: {clientUser.assignedLotIds.length}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => openAssignmentPanel(clientUser)}
                      >
                        Manage access
                      </Button>
                    </div>
                  </div>

                  {expandedUserId === clientUser.id && (
                    <form onSubmit={(event) => handleAssignmentSubmit(event, clientUser)} className="space-y-3 rounded-lg border border-neutral-200 bg-neutral-50 p-4">
                      <div className="flex items-center gap-2 text-sm font-semibold text-neutral-700">
                        <BadgeCheckIcon className="h-4 w-4 text-primary-500" />
                        Assign lot visibility
                      </div>
                      {lotsLoading ? (
                        <p className="text-xs text-neutral-500">Loading lots…</p>
                      ) : (
                        <div className="grid gap-2 md:grid-cols-2">
                          {lots.map((lot) => (
                            <label
                              key={lot.id}
                              className={cn(
                                'flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 text-sm',
                                selectedLotIds.includes(lot.id)
                                  ? 'border-primary-300 bg-primary-50 text-primary-700'
                                  : 'border-neutral-200 bg-white text-neutral-700',
                              )}
                            >
                              <input
                                type="checkbox"
                                className="h-4 w-4"
                                checked={selectedLotIds.includes(lot.id)}
                                onChange={() => toggleLotSelection(lot.id)}
                              />
                              <span className="truncate">{lot.styleRef}</span>
                            </label>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="secondary" size="sm" type="button" onClick={() => setExpandedUserId(null)}>
                          Close
                        </Button>
                        <Button size="sm" type="submit" loading={isSavingAssignments}>
                          Save assignments
                        </Button>
                      </div>
                    </form>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  )
}
