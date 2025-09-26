'use client'

import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { Lot, Factory, LotStatus, UserRole, SupplyChainRole } from '@qa-dashboard/shared'
import { useAuth } from '@/components/providers/auth-provider'
import { formatLotStatus } from '@/lib/utils'

interface LotFormModalProps {
  isOpen: boolean
  onClose: () => void
  initialLot?: Lot | null
}

const STATUS_ORDER: LotStatus[] = [
  LotStatus.PLANNED,
  LotStatus.IN_PRODUCTION,
  LotStatus.INSPECTION,
  LotStatus.PENDING_APPROVAL,
  LotStatus.APPROVED,
  LotStatus.REJECTED,
  LotStatus.SHIPPED,
]

type SupplierRoleDraft = {
  roleId: string
  co2Kg: string
  notes: string
}

type SupplierDraft = {
  factoryId: string
  stage?: string
  isPrimary?: boolean
  roles: SupplierRoleDraft[]
}

const toInputString = (value?: number | string | null) => {
  if (value === undefined || value === null) {
    return ''
  }
  const numeric = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(numeric)) {
    return ''
  }
  return numeric.toString()
}

export function LotFormModal({ isOpen, onClose, initialLot }: LotFormModalProps) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const canEdit = useMemo(
    () => user?.roles?.some((role) => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role)) ?? false,
    [user?.roles],
  )

  const [suppliers, setSuppliers] = useState<SupplierDraft[]>([])
  const [styleRef, setStyleRef] = useState('')
  const [quantityTotal, setQuantityTotal] = useState<number>(0)
  const [status, setStatus] = useState<LotStatus>(LotStatus.PLANNED)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    if (initialLot) {
      if (initialLot.suppliers && initialLot.suppliers.length > 0) {
        setSuppliers(
          initialLot.suppliers
            .slice()
            .sort((a, b) => a.sequence - b.sequence)
            .map((supplier) => ({
              factoryId: supplier.factoryId,
              stage: supplier.stage ?? undefined,
              isPrimary: supplier.isPrimary,
              roles: (supplier.roles ?? []).map((role) => ({
                roleId: role.roleId,
                co2Kg: toInputString(role.co2Kg ?? role.role?.defaultCo2Kg ?? null),
                notes: role.notes ?? '',
              })),
            })),
        )
      } else if (initialLot.factoryId) {
        setSuppliers([{ factoryId: initialLot.factoryId, isPrimary: true, roles: [], stage: undefined }])
      } else {
        setSuppliers([])
      }
      setStyleRef(initialLot.styleRef)
      setQuantityTotal(initialLot.quantityTotal)
      setStatus(initialLot.status)
    } else {
      setSuppliers([])
      setStyleRef('')
      setQuantityTotal(0)
      setStatus(LotStatus.PLANNED)
    }
    setError('')
  }, [initialLot, isOpen])

  const { data: factories = [], isLoading: factoriesLoading } = useQuery<Factory[]>({
    queryKey: ['factories'],
    queryFn: () => apiClient.getFactories(),
    enabled: isOpen,
  })

  const { data: supplyChainRoles = [], isLoading: rolesLoading } = useQuery<SupplyChainRole[]>({
    queryKey: ['supply-chain-roles'],
    queryFn: () => apiClient.getSupplyChainRoles(),
    enabled: isOpen,
  })

  const supplyChainRoleMap = useMemo(
    () => new Map(supplyChainRoles.map((role) => [role.id, role])),
    [supplyChainRoles],
  )

  const supplyChainRoleOrder = useMemo(() => {
    const map = new Map<string, number>()
    supplyChainRoles
      .slice()
      .sort((a, b) => {
        if (a.defaultSequence !== b.defaultSequence) {
          return a.defaultSequence - b.defaultSequence
        }
        return a.name.localeCompare(b.name)
      })
      .forEach((role, index) => {
        map.set(role.id, index)
      })
    return map
  }, [supplyChainRoles])

  const createRoleDraft = (factoryId: string, roleId: string): SupplierRoleDraft => {
    const factory = factories.find((item) => item.id === factoryId)
    const capability = factory?.capabilities?.find((capability) => capability.roleId === roleId)
    const role = capability?.role ?? supplyChainRoleMap.get(roleId)
    const co2Source = capability?.co2OverrideKg ?? role?.defaultCo2Kg ?? null

    return {
      roleId,
      co2Kg: toInputString(co2Source),
      notes: capability?.notes ?? '',
    }
  }

  const createMutation = useMutation({
    mutationFn: (payload: {
      suppliers: Array<{
        factoryId: string
        stage?: string | null
        isPrimary: boolean
        roles: Array<{ roleId: string; sequence: number; co2Kg?: number | null; notes?: string | null }>
      }>
      styleRef: string
      quantityTotal: number
      status: LotStatus
      factoryId?: string
    }) =>
      initialLot
        ? apiClient.updateLot(initialLot.id, payload)
        : apiClient.createLot(payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['lots'] }),
        initialLot ? queryClient.invalidateQueries({ queryKey: ['lot', initialLot.id] }) : Promise.resolve(),
      ])
      onClose()
    },
    onError: (err: any) => {
      setError(err?.message || 'Failed to save lot')
    },
  })

  const toggleSupplier = (factoryId: string) => {
    setSuppliers((current) => {
      const exists = current.find((supplier) => supplier.factoryId === factoryId)
      if (exists) {
        const filtered = current.filter((supplier) => supplier.factoryId !== factoryId)
        if (exists.isPrimary && filtered.length > 0) {
          filtered[0] = { ...filtered[0], isPrimary: true }
        }
        return filtered
      }

      return [
        ...current,
        {
          factoryId,
          isPrimary: current.length === 0,
          stage: undefined,
          roles:
            factories
              .find((item) => item.id === factoryId)
              ?.capabilities?.map((capability) => createRoleDraft(factoryId, capability.roleId)) ?? [],
        },
      ]
    })
  }

  const updateSupplierStage = (factoryId: string, stage: string) => {
    setSuppliers((current) =>
      current.map((supplier) =>
        supplier.factoryId === factoryId ? { ...supplier, stage } : supplier,
      ),
    )
  }

  const toggleSupplierRole = (factoryId: string, roleId: string) => {
    setSuppliers((current) =>
      current.map((supplier) => {
        if (supplier.factoryId !== factoryId) {
          return supplier
        }

        const hasRole = supplier.roles.some((role) => role.roleId === roleId)
        if (hasRole) {
          return {
            ...supplier,
            roles: supplier.roles.filter((role) => role.roleId !== roleId),
          }
        }

        return {
          ...supplier,
          roles: [...supplier.roles, createRoleDraft(factoryId, roleId)],
        }
      }),
    )
  }

  const updateSupplierRoleCo2 = (factoryId: string, roleId: string, value: string) => {
    setSuppliers((current) =>
      current.map((supplier) => {
        if (supplier.factoryId !== factoryId) {
          return supplier
        }

        return {
          ...supplier,
          roles: supplier.roles.map((role) =>
            role.roleId === roleId
              ? {
                  ...role,
                  co2Kg: value,
                }
              : role,
          ),
        }
      }),
    )
  }

  const updateSupplierRoleNotes = (factoryId: string, roleId: string, value: string) => {
    setSuppliers((current) =>
      current.map((supplier) => {
        if (supplier.factoryId !== factoryId) {
          return supplier
        }

        return {
          ...supplier,
          roles: supplier.roles.map((role) =>
            role.roleId === roleId
              ? {
                  ...role,
                  notes: value,
                }
              : role,
          ),
        }
      }),
    )
  }

  const setPrimarySupplier = (factoryId: string) => {
    setSuppliers((current) =>
      current.map((supplier) => ({
        ...supplier,
        isPrimary: supplier.factoryId === factoryId,
      })),
    )
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        <div className="border-b px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {initialLot ? 'Edit Lot' : 'Create New Lot'}
          </h3>
          <p className="text-sm text-gray-500">
            Supply the core lot information your client team needs to track inspections.
          </p>
        </div>

        <form
          className="space-y-4 px-6 py-5"
          onSubmit={(e) => {
            e.preventDefault()
            if (!canEdit) {
              setError('You do not have permission to modify lots')
              return
            }
            if (suppliers.length === 0) {
              setError('Please select at least one supplier factory')
              return
            }
            if (
              !rolesLoading &&
              suppliers.some((supplier) => (supplier.roles ?? []).length === 0)
            ) {
              setError('Assign at least one supply-chain role to each supplier')
              return
            }
            const trimmedStyleRef = styleRef.trim()
            if (!trimmedStyleRef) {
              setError('Style reference is required')
              return
            }
            if (!quantityTotal || quantityTotal <= 0) {
              setError('Quantity must be greater than zero')
              return
            }

            let invalidCo2: string | null = null

            const normalizedSuppliers = suppliers.map((supplier, supplierIndex) => {
              const normalizedRoles = supplier.roles
                .map((role) => {
                  const trimmedCo2 = role.co2Kg.trim()
                  const trimmedNotes = role.notes.trim()

                  if (trimmedCo2 !== '') {
                    const parsed = Number(trimmedCo2)
                    if (Number.isNaN(parsed) || parsed < 0) {
                      invalidCo2 = 'CO₂ contribution must be a non-negative number'
                    }
                  }

                  return {
                    roleId: role.roleId,
                    co2Kg: trimmedCo2 === '' ? undefined : Number(trimmedCo2),
                    notes: trimmedNotes === '' ? undefined : trimmedNotes,
                    order: supplyChainRoleOrder.get(role.roleId) ?? Number.MAX_SAFE_INTEGER,
                  }
                })
                .sort((a, b) => a.order - b.order)
                .map((role, index) => ({
                  roleId: role.roleId,
                  sequence: index,
                  co2Kg: role.co2Kg,
                  notes: role.notes,
                }))

              return {
                factoryId: supplier.factoryId,
                stage: supplier.stage?.trim() ? supplier.stage.trim() : undefined,
                isPrimary: supplier.isPrimary ?? false,
                roles: normalizedRoles,
                originalIndex: supplierIndex,
              }
            })

            if (invalidCo2) {
              setError(invalidCo2)
              return
            }

            if (normalizedSuppliers.some((supplier) => supplier.roles.length === 0)) {
              setError('Assign at least one supply-chain role to each supplier')
              return
            }

            if (!normalizedSuppliers.some((supplier) => supplier.isPrimary)) {
              if (normalizedSuppliers.length > 0) {
                normalizedSuppliers[0] = { ...normalizedSuppliers[0], isPrimary: true }
              }
            }

            const primaryFactoryId = normalizedSuppliers.find((supplier) => supplier.isPrimary)?.factoryId

            if (!primaryFactoryId) {
              setError('Primary supplier is required')
              return
            }

            const submissionSuppliers = normalizedSuppliers
              .sort((a, b) => a.originalIndex - b.originalIndex)
              .map((supplier) => ({
                factoryId: supplier.factoryId,
                stage: supplier.stage,
                isPrimary: supplier.isPrimary,
                roles: supplier.roles,
              }))

            setError('')
            createMutation.mutate({
              suppliers: submissionSuppliers,
              factoryId: primaryFactoryId,
              styleRef: trimmedStyleRef,
              quantityTotal,
              status,
            })
          }}
        >
          {error && (
            <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Supplier factories</label>
            <div className="space-y-3">
              {factoriesLoading ? (
                <div className="rounded-md border border-dashed border-gray-200 p-4 text-sm text-gray-500">
                  Loading factories…
                </div>
              ) : factories.length === 0 ? (
                <div className="rounded-md border border-dashed border-gray-200 p-4 text-sm text-gray-500">
                  No factories available. Add suppliers from the Factories screen first.
                </div>
              ) : (
                factories.map((factory) => {
                  const supplier = suppliers.find((item) => item.factoryId === factory.id)
                  const isSelected = Boolean(supplier)
                  const capabilityRoles = (factory.capabilities ?? [])
                    .map((capability) => capability.role ?? supplyChainRoleMap.get(capability.roleId))
                    .filter((role): role is SupplyChainRole => Boolean(role))
                  const sortedCapabilityRoles = capabilityRoles.slice().sort((a, b) => {
                    if (a.defaultSequence !== b.defaultSequence) {
                      return a.defaultSequence - b.defaultSequence
                    }
                    return a.name.localeCompare(b.name)
                  })

                  return (
                    <div key={factory.id} className="rounded-md border border-gray-200 p-3">
                      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                        <label className="flex items-center space-x-3 text-sm font-medium text-gray-700">
                          <input
                            type="checkbox"
                            className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                            checked={isSelected}
                            disabled={createMutation.isPending}
                            onChange={() => toggleSupplier(factory.id)}
                          />
                          <span>
                            {factory.name}
                            {factory.city ? ` • ${factory.city}` : ''}
                          </span>
                        </label>
                        {isSelected && (
                          <label className="flex items-center space-x-2 text-xs text-gray-600">
                            <input
                              type="radio"
                              name="primarySupplier"
                              className="h-3 w-3 text-primary-600 focus:ring-primary-500"
                              checked={supplier?.isPrimary ?? false}
                              onChange={() => setPrimarySupplier(factory.id)}
                              disabled={createMutation.isPending}
                            />
                            <span>Primary supplier</span>
                          </label>
                        )}
                      </div>
                      {isSelected && (
                        <div className="mt-3 space-y-4">
                          <div>
                            <label className="mb-1 block text-xs font-semibold text-gray-500">Production stage (optional)</label>
                            <input
                              type="text"
                              value={supplier?.stage ?? ''}
                              onChange={(e) => updateSupplierStage(factory.id, e.target.value)}
                              disabled={createMutation.isPending}
                              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                              placeholder="e.g. Cutting, Assembly"
                            />
                          </div>

                          <div>
                            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                              Supply-chain roles for this supplier
                            </p>
                            {rolesLoading ? (
                              <div className="rounded-md border border-dashed border-gray-200 p-3 text-xs text-gray-500">
                                Loading roles…
                              </div>
                            ) : sortedCapabilityRoles.length === 0 ? (
                              <div className="rounded-md border border-dashed border-gray-200 p-3 text-xs text-gray-500">
                                Assign capabilities to {factory.name} from the Factories panel first.
                              </div>
                            ) : (
                              sortedCapabilityRoles.map((role) => {
                                const roleDraft = supplier?.roles.find((item) => item.roleId === role.id)
                                return (
                                  <div key={role.id} className="rounded-md border border-gray-200 px-3 py-2">
                                    <label className="flex items-start space-x-3 text-xs text-gray-700">
                                      <input
                                        type="checkbox"
                                        className="mt-0.5 h-4 w-4 text-primary-600 focus:ring-primary-500"
                                        checked={Boolean(roleDraft)}
                                        disabled={createMutation.isPending}
                                        onChange={() => toggleSupplierRole(factory.id, role.id)}
                                      />
                                      <span>
                                        <span className="font-medium text-gray-900">{role.name}</span>
                                        {role.description && (
                                          <span className="block text-[11px] text-gray-500">{role.description}</span>
                                        )}
                                        <span className="block text-[11px] text-gray-400">
                                          Default CO₂: {Number(role.defaultCo2Kg ?? 0).toFixed(2)} kg
                                        </span>
                                      </span>
                                    </label>
                                    {roleDraft && (
                                      <div className="mt-3 grid gap-3 text-[11px] text-gray-600 md:grid-cols-2">
                                        <div>
                                          <label className="mb-1 block font-semibold text-gray-600">
                                            CO₂ contribution (kg)
                                          </label>
                                          <input
                                            type="number"
                                            min={0}
                                            step="0.01"
                                            value={roleDraft.co2Kg}
                                            onChange={(e) => updateSupplierRoleCo2(factory.id, role.id, e.target.value)}
                                            disabled={createMutation.isPending}
                                            className="block w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                                            placeholder="Use default if empty"
                                          />
                                        </div>
                                        <div>
                                          <label className="mb-1 block font-semibold text-gray-600">Notes</label>
                                          <input
                                            type="text"
                                            value={roleDraft.notes}
                                            onChange={(e) => updateSupplierRoleNotes(factory.id, role.id, e.target.value)}
                                            disabled={createMutation.isPending}
                                            className="block w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                                            placeholder="Optional"
                                          />
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                )
                              })
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Select every factory that touched this lot. Mark the factory currently responsible as primary.
            </p>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Style reference</label>
            <input
              type="text"
              value={styleRef}
              onChange={(e) => setStyleRef(e.target.value)}
              disabled={createMutation.isPending}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              placeholder="e.g. HM-SS24-001"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Quantity</label>
            <input
              type="number"
              min={1}
              value={quantityTotal || ''}
              onChange={(e) => setQuantityTotal(Number(e.target.value))}
              disabled={createMutation.isPending}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              placeholder="Total units in the lot"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">Status</label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as LotStatus)}
            disabled={createMutation.isPending}
            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
          >
            {STATUS_ORDER.map((value) => (
              <option key={value} value={value}>
                {formatLotStatus(value)}
              </option>
            ))}
          </select>
        </div>

          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={() => {
                if (createMutation.isPending) return
                onClose()
              }}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 disabled:opacity-60"
            >
              {createMutation.isPending ? (initialLot ? 'Saving…' : 'Creating…') : initialLot ? 'Save changes' : 'Create lot'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
