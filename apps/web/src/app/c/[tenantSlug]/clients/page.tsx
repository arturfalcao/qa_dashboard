'use client'

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Client } from '@qa-dashboard/shared'
import { PageHeader } from '@/components/ui/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { EmptyState } from '@/components/ui/empty-state'
import { Modal, ModalFooter } from '@/components/ui/modal'
import { Input, TextArea } from '@/components/ui/input'
import { useToast } from '@/components/ui/toast'
import { MailIcon, PhoneIcon, MapPinIcon, UsersIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function ClientsPage() {
  const queryClient = useQueryClient()
  const { publish } = useToast()

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingClient, setEditingClient] = useState<Client | null>(null)
  const [pendingDelete, setPendingDelete] = useState<Client | null>(null)

  const { data: clients = [], isLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: () => apiClient.listClients(),
  })

  const summary = useMemo(() => {
    const total = clients.length
    const active = clients.filter((client) => client.isActive).length
    const inactive = total - active
    const countries = new Set(clients.map((client) => client.country).filter(Boolean))

    return {
      total,
      active,
      inactive,
      countries: countries.size,
    }
  }, [clients])

  const createMutation = useMutation({
    mutationFn: (payload: {
      name: string
      contactEmail?: string
      contactPhone?: string
      address?: string
      country?: string
      notes?: string
    }) => apiClient.createClient(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setIsModalOpen(false)
      setEditingClient(null)
      publish({
        variant: 'success',
        title: 'Client created',
        description: 'The client has been added successfully.',
      })
    },
    onError: (error: any) => {
      publish({
        variant: 'danger',
        title: 'Unable to create client',
        description: error?.message || 'Please retry in a moment.',
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, ...payload }: { id: string } & Partial<Client>) => {
      const cleanPayload = Object.fromEntries(
        Object.entries(payload).map(([key, value]) => [key, value === null ? undefined : value]),
      )
      return apiClient.updateClient(id, cleanPayload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setIsModalOpen(false)
      setEditingClient(null)
      publish({ variant: 'success', title: 'Client updated', description: 'Changes saved.' })
    },
    onError: (error: any) => {
      publish({
        variant: 'danger',
        title: 'Unable to update client',
        description: error?.message || 'Please retry in a moment.',
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteClient(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      publish({ variant: 'success', title: 'Client removed' })
      setPendingDelete(null)
    },
    onError: (error: any) => {
      publish({
        variant: 'danger',
        title: 'Unable to delete client',
        description: error?.message || 'Please retry in a moment.',
      })
    },
  })

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const payload = {
      name: (formData.get('name') as string) || '',
      contactEmail: (formData.get('contactEmail') as string) || undefined,
      contactPhone: (formData.get('contactPhone') as string) || undefined,
      address: (formData.get('address') as string) || undefined,
      country: (formData.get('country') as string) || undefined,
      notes: (formData.get('notes') as string) || undefined,
    }

    if (!payload.name.trim()) {
      publish({ variant: 'danger', title: 'Name is required' })
      return
    }

    if (editingClient) {
      updateMutation.mutate({ id: editingClient.id, ...payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  const openCreateModal = () => {
    setEditingClient(null)
    setIsModalOpen(true)
  }

  const openEditModal = (client: Client) => {
    setEditingClient(client)
    setIsModalOpen(true)
  }

  const pageActions = (
    <Button onClick={openCreateModal}>
      New client
    </Button>
  )

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Clients"
          description="Manage your customer accounts and their information."
          actions={pageActions}
        />
        <Card>
          <CardContent className="flex h-48 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary-200 border-t-primary-600" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Clients"
        description="Manage your customer accounts and their information."
        actions={pageActions}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Total clients</CardDescription>
            <CardTitle>{summary.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Active</CardDescription>
            <CardTitle>{summary.active}</CardTitle>
            <CardDescription>{summary.inactive} inactive</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Countries</CardDescription>
            <CardTitle>{summary.countries}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Key contacts</CardDescription>
            <CardTitle>{clients.filter((client) => client.contactEmail).length}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <CardTitle>Client directory</CardTitle>
            <CardDescription>Keep track of contact details and status at a glance.</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {clients.length === 0 ? (
            <EmptyState
              icon={<UsersIcon className="h-5 w-5" />}
              title="No clients yet"
              description="Start by creating your first client profile."
              action={{ label: 'Create client', onClick: openCreateModal }}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {clients.map((client) => (
                  <TableRow key={client.id}>
                    <TableCell>
                      <div className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                        {client.name}
                      </div>
                      {client.notes && (
                        <p className="text-xs text-neutral-500">{client.notes}</p>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1 text-sm text-neutral-700 dark:text-neutral-300">
                        <span className="inline-flex items-center gap-2">
                          <MailIcon className="h-4 w-4 text-neutral-400" />
                          {client.contactEmail || '—'}
                        </span>
                        <span className="inline-flex items-center gap-2">
                          <PhoneIcon className="h-4 w-4 text-neutral-400" />
                          {client.contactPhone || '—'}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-300">
                        <MapPinIcon className="h-4 w-4 text-neutral-400" />
                        {[client.address, client.country].filter(Boolean).join(', ') || '—'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          'inline-flex rounded-full px-3 py-1 text-xs font-semibold',
                          client.isActive
                            ? 'bg-success-100 text-success-700'
                            : 'bg-neutral-200 text-neutral-600',
                        )}
                      >
                        {client.isActive ? 'Active' : 'Inactive'}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="secondary" size="sm" onClick={() => openEditModal(client)}>
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-danger-600 hover:text-danger-700"
                          onClick={() => setPendingDelete(client)}
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {isModalOpen && (
        <Modal
          open
          onClose={() => {
            setIsModalOpen(false)
            setEditingClient(null)
          }}
          title={editingClient ? 'Edit client' : 'Create client'}
          description={editingClient ? 'Update contact details and metadata.' : 'Add a new brand or customer profile.'}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700 dark:text-neutral-300" htmlFor="client-name">
                Client name
              </label>
              <Input
                id="client-name"
                name="name"
                defaultValue={editingClient?.name ?? ''}
                placeholder="e.g., Arket, Cos, Ganni"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-neutral-700 dark:text-neutral-300" htmlFor="client-email">
                  Contact email
                </label>
                <Input
                  id="client-email"
                  type="email"
                  name="contactEmail"
                  defaultValue={editingClient?.contactEmail ?? ''}
                  placeholder="contact@brand.com"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-neutral-700 dark:text-neutral-300" htmlFor="client-phone">
                  Contact phone
                </label>
                <Input
                  id="client-phone"
                  type="tel"
                  name="contactPhone"
                  defaultValue={editingClient?.contactPhone ?? ''}
                  placeholder="+351 912 345 678"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700 dark:text-neutral-300" htmlFor="client-address">
                Address
              </label>
              <Input
                id="client-address"
                name="address"
                defaultValue={editingClient?.address ?? ''}
                placeholder="Street, city, postal code"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700 dark:text-neutral-300" htmlFor="client-country">
                Country
              </label>
              <Input
                id="client-country"
                name="country"
                defaultValue={editingClient?.country ?? ''}
                placeholder="e.g., Portugal"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-neutral-700 dark:text-neutral-300" htmlFor="client-notes">
                Notes
              </label>
              <TextArea
                id="client-notes"
                name="notes"
                defaultValue={editingClient?.notes ?? ''}
                placeholder="Add context or commercial notes for this client."
                rows={3}
              />
            </div>

            <ModalFooter>
              <Button
                variant="secondary"
                type="button"
                onClick={() => {
                  setIsModalOpen(false)
                  setEditingClient(null)
                }}
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingClient ? 'Save changes' : 'Create client'}
              </Button>
            </ModalFooter>
          </form>
        </Modal>
      )}

      {pendingDelete && (
        <Modal
          open
          onClose={() => setPendingDelete(null)}
          title="Remove client"
          description={`This will delete ${pendingDelete.name} and its saved details.`}
        >
          <p className="text-sm text-neutral-600">
            This action cannot be undone. Historical lots and reports remain available, but the client will no longer appear in selection lists.
          </p>
          <ModalFooter>
            <Button variant="secondary" onClick={() => setPendingDelete(null)} disabled={deleteMutation.isPending}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => deleteMutation.mutate(pendingDelete.id)}
              loading={deleteMutation.isPending}
            >
              Delete client
            </Button>
          </ModalFooter>
        </Modal>
      )}
    </div>
  )
}
