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
  const isAdmin = useMemo(() => user?.roles?.includes(UserRole.ADMIN) ?? false, [user?.roles])

  const [suppliers, setSuppliers] = useState<SupplierDraft[]>([])
  const [selectedClientId, setSelectedClientId] = useState<string>('')
  const [styleRef, setStyleRef] = useState('')
  const [quantityTotal, setQuantityTotal] = useState<number>(0)
  const [status, setStatus] = useState<LotStatus>(LotStatus.PLANNED)
  const [error, setError] = useState<string>('')

  // DPP Hub Data fields
  const [materialComposition, setMaterialComposition] = useState<Array<{fiber: string; percentage: number}>>([])
  const [dyeLot, setDyeLot] = useState('')
  const [certifications, setCertifications] = useState<Array<{type: string}>>([])
  const [dppMetadata, setDppMetadata] = useState('')

  // Tech Pack fields
  const [techPackFile, setTechPackFile] = useState<File | null>(null)
  const [uploadingTechPack, setUploadingTechPack] = useState(false)
  const [techPackStatus, setTechPackStatus] = useState<string | null>(null)
  const [techPackData, setTechPackData] = useState<any>(null)

  // Size specifications
  const [sizeSpecifications, setSizeSpecifications] = useState<Array<{
    size: string
    quantity: number
    measurements: Record<string, number>
  }>>([])

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

      // Load DPP hub data if available
      setMaterialComposition((initialLot as any).materialComposition || [])
      setDyeLot((initialLot as any).dyeLot || '')
      setCertifications(((initialLot as any).certifications || []).map((cert: any) => ({ type: cert.type })))
      setDppMetadata((initialLot as any).dppMetadata ? JSON.stringify((initialLot as any).dppMetadata, null, 2) : '')

      // Load size specifications if available
      setSizeSpecifications((initialLot as any).sizeSpecifications || [])
    } else {
      setSuppliers([])
      setSelectedClientId('')
      setStyleRef('')
      setQuantityTotal(0)
      setStatus(LotStatus.PLANNED)

      // Reset DPP hub data for new lots
      setMaterialComposition([])
      setDyeLot('')
      setCertifications([])
      setDppMetadata('')
      setSizeSpecifications([])
    }
    setError('')
  }, [initialLot, isOpen])

  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: () => apiClient.listClients(),
    enabled: isOpen,
  })

  const { data: allFactories = [], isLoading: factoriesLoading } = useQuery<Factory[]>({
    queryKey: ['factories'],
    queryFn: () => apiClient.getFactories(),
    enabled: isOpen,
  })

  // Filter factories based on selected client's tenant (for admins) or user's tenant
  const factories = useMemo(() => {
    let targetTenantId: string | undefined

    if (isAdmin && selectedClientId) {
      // Admin selected a client, find the client's tenantId
      const selectedClient = clients.find((c) => c.id === selectedClientId)
      targetTenantId = selectedClient?.tenantId
    } else if (!isAdmin) {
      // Non-admin user, use their tenantId
      targetTenantId = user?.tenantId ?? undefined
    }

    if (!targetTenantId) {
      return []
    }

    return allFactories.filter((factory) => factory.tenantId === targetTenantId)
  }, [allFactories, isAdmin, selectedClientId, clients, user?.tenantId])

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
    mutationFn: async (payload: {
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
      // DPP Hub fields
      materialComposition?: Array<{ fiber: string; percentage: number; properties?: Record<string, any> }>
      dyeLot?: string
      certifications?: Array<{ type: string }>
      dppMetadata?: Record<string, any>
    }) => {
      let lot: Lot
      if (initialLot) {
        lot = await apiClient.updateLot(initialLot.id, payload)
      } else {
        lot = await apiClient.createLot(payload)

        // If creating a new lot and there's a tech pack file, upload it
        if (techPackFile) {
          try {
            const uploadResult = await apiClient.uploadTechPack(lot.id, techPackFile)
            console.log('Tech pack uploaded successfully:', uploadResult)
            // Refresh the lot data to get the updated tech pack fields
            await queryClient.invalidateQueries({ queryKey: ['lot', lot.id] })
          } catch (err: any) {
            // Log error but don't fail the entire operation
            console.error('Tech pack upload failed:', err)
            // Show a more user-friendly error
            const errorMessage = err.message || 'Unknown error'
            console.warn(`Tech pack upload error: ${errorMessage}`)
            // Note: The lot is still created, just without the tech pack
            // User can try uploading the tech pack again from the edit form
          }
        }
      }
      return lot
    },
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
      <div className="w-full max-w-3xl max-h-[90vh] rounded-lg bg-white shadow-xl flex flex-col">
        <div className="border-b px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {initialLot ? 'Edit Lot' : 'Create New Lot'}
          </h3>
          <p className="text-sm text-gray-500">
            Supply the core lot information your client team needs to track inspections.
          </p>
        </div>

        <form
          className="flex-1 overflow-y-auto space-y-4 px-6 py-5"
          onSubmit={(e) => {
            e.preventDefault()
            if (!canEdit) {
              setError('You do not have permission to modify lots')
              return
            }
            if (isAdmin && !selectedClientId && !initialLot) {
              setError('Please select a client')
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

            // Parse DPP metadata if provided
            let parsedDppMetadata: Record<string, any> | undefined = undefined
            if (dppMetadata.trim()) {
              try {
                parsedDppMetadata = JSON.parse(dppMetadata.trim())
              } catch (err) {
                setError('DPP Metadata must be valid JSON')
                return
              }
            }

            const payload = {
              clientId: isAdmin && selectedClientId ? selectedClientId : undefined,
              suppliers: submissionSuppliers,
              factoryId: primaryFactoryId,
              styleRef: trimmedStyleRef,
              quantityTotal,
              status,
              // DPP Hub data
              materialComposition: materialComposition.length > 0 ? materialComposition : undefined,
              dyeLot: dyeLot.trim() || undefined,
              certifications: certifications.length > 0 ? certifications : undefined,
              dppMetadata: parsedDppMetadata,
              // Size specifications
              sizeSpecifications: sizeSpecifications.length > 0 ? sizeSpecifications : undefined,
            }

            console.log('Lot payload:', JSON.stringify(payload, null, 2))
            setError('')
            createMutation.mutate(payload)
          }}
        >
          {error && (
            <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          {isAdmin && !initialLot && (
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Client</label>
              <select
                value={selectedClientId}
                onChange={(e) => {
                  setSelectedClientId(e.target.value)
                  // Reset suppliers when client changes since factories will change
                  setSuppliers([])
                }}
                disabled={createMutation.isPending}
                required
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              >
                <option value="">Select a client...</option>
                {clients.map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.name}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                Select which client this lot belongs to
              </p>
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

        {/* DPP Hub Data Section */}
        <div className="border-t pt-4">
          <h4 className="mb-4 text-sm font-semibold text-gray-900">DPP Hub Data</h4>
          <p className="mb-4 text-xs text-gray-500">
            Digital Product Passport data for EU compliance and traceability
          </p>

          {/* Material Composition */}
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">Material Composition</label>
            <div className="space-y-2">
              {materialComposition.map((material, index) => (
                <div key={index} className="flex items-center space-x-3">
                  <input
                    type="text"
                    placeholder="Fiber (e.g. Cotton)"
                    value={material.fiber}
                    onChange={(e) => {
                      const updated = [...materialComposition]
                      updated[index].fiber = e.target.value
                      setMaterialComposition(updated)
                    }}
                    className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                  />
                  <input
                    type="number"
                    placeholder="% (e.g. 80)"
                    min={0}
                    max={100}
                    value={material.percentage || ''}
                    onChange={(e) => {
                      const updated = [...materialComposition]
                      updated[index].percentage = Number(e.target.value)
                      setMaterialComposition(updated)
                    }}
                    className="w-24 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const updated = materialComposition.filter((_, i) => i !== index)
                      setMaterialComposition(updated)
                    }}
                    className="text-red-600 hover:text-red-700"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => {
                  setMaterialComposition([...materialComposition, { fiber: '', percentage: 0 }])
                }}
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                + Add Material
              </button>
            </div>
          </div>

          {/* Dye Lot */}
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">Dye Lot</label>
            <input
              type="text"
              value={dyeLot}
              onChange={(e) => setDyeLot(e.target.value)}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              placeholder="e.g. HM-SS25-517-D1"
            />
            <p className="mt-1 text-xs text-gray-500">
              Dye lot identifier for traceability
            </p>
          </div>

          {/* Certifications */}
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">Certifications</label>
            <div className="space-y-2">
              {[
                'Global Organic Textile Standard (GOTS)',
                'OEKO-TEX Standard 100',
                'Global Recycled Standard (GRS)',
                'Recycled Claim Standard (RCS)',
                'ISO 14001',
                'Bluesign',
                'amfori BSCI'
              ].map((certType) => (
                <label key={certType} className="flex items-center space-x-3 text-sm">
                  <input
                    type="checkbox"
                    checked={certifications.some(cert => cert.type === certType)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setCertifications([...certifications, { type: certType }])
                      } else {
                        setCertifications(certifications.filter(cert => cert.type !== certType))
                      }
                    }}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-gray-700">{certType}</span>
                </label>
              ))}
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Select the certifications applicable to this lot
            </p>
          </div>

          {/* DPP Metadata */}
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">DPP Metadata</label>
            <textarea
              value={dppMetadata}
              onChange={(e) => setDppMetadata(e.target.value)}
              rows={4}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
              placeholder='Additional metadata as JSON, e.g. {"origin": "Portugal", "sustainabilityScore": 95}'
            />
            <p className="mt-1 text-xs text-gray-500">
              Optional JSON metadata for additional DPP information
            </p>
          </div>
        </div>

        {/* Size Specifications Section */}
        <div className="border-t pt-4">
          <h4 className="mb-4 text-sm font-semibold text-gray-900">Size Specifications</h4>
          <p className="mb-4 text-xs text-gray-500">
            Add size breakdown with quantities and measurements (optional)
          </p>

          <div className="space-y-3">
            {sizeSpecifications.map((sizeSpec, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-3 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1 grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1 block text-xs font-medium text-gray-700">Size</label>
                      <input
                        type="text"
                        placeholder="e.g. S, M, L, 38, 40"
                        value={sizeSpec.size}
                        onChange={(e) => {
                          const updated = [...sizeSpecifications]
                          updated[index].size = e.target.value
                          setSizeSpecifications(updated)
                        }}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-xs font-medium text-gray-700">Quantity</label>
                      <input
                        type="number"
                        min={0}
                        placeholder="e.g. 500"
                        value={sizeSpec.quantity || ''}
                        onChange={(e) => {
                          const updated = [...sizeSpecifications]
                          updated[index].quantity = Number(e.target.value)
                          setSizeSpecifications(updated)
                        }}
                        className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                      />
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSizeSpecifications(sizeSpecifications.filter((_, i) => i !== index))
                    }}
                    className="ml-3 text-red-600 hover:text-red-700 text-sm"
                  >
                    Remove
                  </button>
                </div>

                {/* Measurements */}
                <div>
                  <label className="mb-2 block text-xs font-medium text-gray-700">Measurements (cm)</label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {(() => {
                      const predefinedMeasurements = ['chest', 'length', 'sleeve', 'shoulder', 'waist', 'hip']
                      const existingMeasurements = Object.keys(sizeSpec.measurements || {})
                      const allMeasurements = Array.from(new Set([...predefinedMeasurements, ...existingMeasurements]))

                      return allMeasurements.map((measurementType) => (
                        <div key={measurementType} className="relative">
                          <input
                            type="number"
                            step="0.1"
                            placeholder={measurementType.charAt(0).toUpperCase() + measurementType.slice(1)}
                            value={sizeSpec.measurements?.[measurementType] || ''}
                            onChange={(e) => {
                              const updated = [...sizeSpecifications]
                              if (!updated[index].measurements) {
                                updated[index].measurements = {}
                              }
                              if (e.target.value) {
                                updated[index].measurements[measurementType] = Number(e.target.value)
                              } else {
                                delete updated[index].measurements[measurementType]
                              }
                              setSizeSpecifications(updated)
                            }}
                            className="block w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs shadow-sm focus:border-primary-500 focus:outline-none focus:ring-primary-500"
                          />
                          {!predefinedMeasurements.includes(measurementType) && (
                            <button
                              type="button"
                              onClick={() => {
                                const updated = [...sizeSpecifications]
                                if (updated[index].measurements) {
                                  delete updated[index].measurements[measurementType]
                                  setSizeSpecifications(updated)
                                }
                              }}
                              className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-4 h-4 flex items-center justify-center text-xs hover:bg-red-600"
                              title="Remove custom measurement"
                            >
                              ×
                            </button>
                          )}
                        </div>
                      ))
                    })()}
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      const newMeasurement = prompt('Enter measurement name (e.g., inseam, cuff):')
                      if (newMeasurement) {
                        const updated = [...sizeSpecifications]
                        if (!updated[index].measurements) {
                          updated[index].measurements = {}
                        }
                        updated[index].measurements[newMeasurement.toLowerCase()] = 0
                        setSizeSpecifications(updated)
                      }
                    }}
                    className="mt-2 text-xs text-primary-600 hover:text-primary-700"
                  >
                    + Add custom measurement
                  </button>
                </div>
              </div>
            ))}

            <button
              type="button"
              onClick={() => {
                setSizeSpecifications([
                  ...sizeSpecifications,
                  { size: '', quantity: 0, measurements: {} }
                ])
              }}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              + Add Size
            </button>
          </div>

          <p className="mt-2 text-xs text-gray-500">
            Total from sizes: {sizeSpecifications.reduce((sum, spec) => sum + (spec.quantity || 0), 0)} units
            {quantityTotal > 0 && sizeSpecifications.length > 0 && (
              sizeSpecifications.reduce((sum, spec) => sum + (spec.quantity || 0), 0) !== quantityTotal ? (
                <span className="ml-2 text-yellow-600">
                  (Warning: doesn't match total quantity)
                </span>
              ) : (
                <span className="ml-2 text-green-600">
                  ✓ Matches total quantity
                </span>
              )
            )}
          </p>
        </div>

        {/* Tech Pack Upload Section */}
        <div className="border-t pt-4">
          <h4 className="mb-4 text-sm font-semibold text-gray-900">Tech Pack Upload</h4>
          <p className="mb-4 text-xs text-gray-500">
            Upload a tech pack file to automatically extract product specifications and measurements
          </p>

          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">Tech Pack File</label>
            <div className="flex items-center space-x-3">
              <input
                type="file"
                accept=".pdf,.xlsx,.xls,.csv,.jpg,.jpeg,.png,.gif"
                onChange={(e) => {
                  const file = e.target.files?.[0] || null
                  setTechPackFile(file)
                }}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border file:border-gray-300 file:text-sm file:font-medium file:text-gray-700 file:bg-gray-50 hover:file:bg-gray-100"
              />
              {techPackFile && (
                <button
                  type="button"
                  onClick={() => setTechPackFile(null)}
                  className="text-red-600 hover:text-red-700 text-sm"
                >
                  Remove
                </button>
              )}
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Supported formats: PDF, Excel, CSV, Images (JPG, PNG)
            </p>
          </div>

          {techPackFile && !initialLot && (
            <div className="mb-4">
              <button
                type="button"
                onClick={async () => {
                  setUploadingTechPack(true)
                  setError('')
                  try {
                    // Note: For new lots, we'll upload the tech pack after the lot is created
                    // For now, just show that it's selected
                    setTechPackStatus('ready')
                  } catch (err: any) {
                    setError(`Tech pack processing failed: ${err.message}`)
                  } finally {
                    setUploadingTechPack(false)
                  }
                }}
                disabled={uploadingTechPack}
                className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 disabled:opacity-60"
              >
                {uploadingTechPack ? 'Processing...' : 'Process Tech Pack'}
              </button>
              <p className="mt-2 text-xs text-gray-500">
                The tech pack will be processed after the lot is created
              </p>
            </div>
          )}

          {initialLot && techPackFile && (
            <div className="mb-4">
              <button
                type="button"
                onClick={async () => {
                  if (!techPackFile) return
                  setUploadingTechPack(true)
                  setError('')
                  try {
                    const result = await apiClient.uploadTechPack(initialLot.id, techPackFile)

                    // Update form fields with extracted data
                    if (result.extractedData) {
                      if (result.extractedData.styleRef) {
                        setStyleRef(result.extractedData.styleRef)
                      }
                      if (result.extractedData.materialComposition) {
                        setMaterialComposition(result.extractedData.materialComposition)
                      }
                      if (result.extractedData.dyeLot) {
                        setDyeLot(result.extractedData.dyeLot)
                      }
                      if (result.extractedData.productionQuantity) {
                        setQuantityTotal(result.extractedData.productionQuantity)
                      }
                    }

                    setTechPackStatus('completed')
                    setTechPackData(result.extractedData)
                    setTechPackFile(null)

                    // Show success message
                    setError('') // Clear any previous errors
                    alert('Tech pack uploaded and processed successfully!')
                  } catch (err: any) {
                    setError(`Tech pack upload failed: ${err.message}`)
                    setTechPackStatus('failed')
                  } finally {
                    setUploadingTechPack(false)
                  }
                }}
                disabled={uploadingTechPack}
                className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 disabled:opacity-60"
              >
                {uploadingTechPack ? 'Processing...' : 'Upload & Process Tech Pack'}
              </button>
            </div>
          )}

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
