'use client'

import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { Factory, LotStatus, UserRole, SupplyChainRole, GarmentType } from '@qa-dashboard/shared'
import { useAuth } from '@/components/providers/auth-provider'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { formatLotStatus } from '@/lib/utils'
import { Package, Sparkles, CheckCircle2 } from 'lucide-react'

interface TechPack {
  id: string
  tenantId: string
  styleRef: string
  productName?: string
  season?: string
  designer?: string
  sampleSize?: string
  materialComposition?: any[]
  colorways?: any[]
  sizeSpecifications?: any[]
  measurementTolerances?: Record<string, number>
}

interface CreateLotFromTechPackModalProps {
  isOpen: boolean
  onClose: () => void
  techPack: TechPack
  tenantSlug: string
}

const STATUS_ORDER: LotStatus[] = [
  LotStatus.PLANNED,
  LotStatus.IN_PRODUCTION,
  LotStatus.INSPECTION,
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

export function CreateLotFromTechPackModal({
  isOpen,
  onClose,
  techPack,
  tenantSlug,
}: CreateLotFromTechPackModalProps) {
  const router = useRouter()
  const { user } = useAuth()
  const queryClient = useQueryClient()

  // Form state - pre-filled from TechPack
  const [styleRef, setStyleRef] = useState('')
  const [quantityTotal, setQuantityTotal] = useState<number>(0)
  const [status, setStatus] = useState<LotStatus>(LotStatus.PLANNED)
  const [suppliers, setSuppliers] = useState<SupplierDraft[]>([])
  const [error, setError] = useState<string>('')

  // Initialize form with TechPack data
  useEffect(() => {
    if (isOpen && techPack) {
      setStyleRef(techPack.styleRef || '')
      // Calculate total quantity from size specs if available
      if (techPack.sizeSpecifications && techPack.sizeSpecifications.length > 0) {
        const total = techPack.sizeSpecifications.reduce((sum: number, spec: any) => {
          const qty = spec.quantity || spec.qty || 0
          return sum + qty
        }, 0)
        if (total > 0) {
          setQuantityTotal(total)
        }
      }
      setStatus(LotStatus.PLANNED)
      setSuppliers([])
      setError('')
    }
  }, [isOpen, techPack])

  const { data: allFactories = [], isLoading: factoriesLoading } = useQuery<Factory[]>({
    queryKey: ['factories'],
    queryFn: () => apiClient.getFactories(),
    enabled: isOpen,
  })

  const { data: supplyChainRoles = [], isLoading: rolesLoading } = useQuery<SupplyChainRole[]>({
    queryKey: ['supply-chain-roles'],
    queryFn: () => apiClient.getSupplyChainRoles(),
    enabled: isOpen,
  })

  // Filter factories by tenant
  const factories = useMemo(() => {
    if (!user?.tenantId) return []
    return allFactories.filter((factory) => factory.tenantId === user.tenantId)
  }, [allFactories, user?.tenantId])

  const supplyChainRoleMap = useMemo(
    () => new Map(supplyChainRoles.map((role) => [role.id, role])),
    [supplyChainRoles],
  )

  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      return apiClient.createLot(payload)
    },
    onSuccess: async (lot) => {
      // Link the lot to the tech pack
      try {
        await apiClient.updateLot(lot.id, { techPackId: techPack.id } as any)
      } catch (err) {
        console.error('Failed to link tech pack to lot:', err)
      }

      await queryClient.invalidateQueries({ queryKey: ['lots'] })
      await queryClient.invalidateQueries({ queryKey: ['tech-pack-lots', techPack.id] })
      onClose()
      router.push(`/c/${tenantSlug}/lots/${lot.id}`)
    },
    onError: (err: any) => {
      setError(err?.message || 'Failed to create lot')
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
          roles: [],
        },
      ]
    })
  }

  const toggleSupplierRole = (factoryId: string, roleId: string) => {
    setSuppliers((current) =>
      current.map((supplier) => {
        if (supplier.factoryId !== factoryId) return supplier

        const hasRole = supplier.roles.some((role) => role.roleId === roleId)
        if (hasRole) {
          return {
            ...supplier,
            roles: supplier.roles.filter((role) => role.roleId !== roleId),
          }
        }

        const role = supplyChainRoleMap.get(roleId)
        return {
          ...supplier,
          roles: [
            ...supplier.roles,
            {
              roleId,
              co2Kg: role?.defaultCo2Kg?.toString() || '',
              notes: '',
            },
          ],
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (suppliers.length === 0) {
      setError('Please select at least one supplier factory')
      return
    }

    if (suppliers.some((supplier) => supplier.roles.length === 0)) {
      setError('Assign at least one supply-chain role to each supplier')
      return
    }

    if (!styleRef.trim()) {
      setError('Style reference is required')
      return
    }

    if (!quantityTotal || quantityTotal <= 0) {
      setError('Quantity must be greater than zero')
      return
    }

    const primaryFactoryId = suppliers.find((s) => s.isPrimary)?.factoryId || suppliers[0]?.factoryId

    const normalizedSuppliers = suppliers.map((supplier, index) => ({
      factoryId: supplier.factoryId,
      stage: supplier.stage?.trim() || undefined,
      isPrimary: supplier.isPrimary ?? index === 0,
      roles: supplier.roles.map((role, roleIndex) => ({
        roleId: role.roleId,
        sequence: roleIndex,
        co2Kg: role.co2Kg ? Number(role.co2Kg) : undefined,
        notes: role.notes?.trim() || undefined,
      })),
    }))

    // Convert TechPack material composition to Lot format
    const materialComposition = techPack.materialComposition?.map((mat: any) => ({
      fiber: mat.material || mat.name || mat.fiber || 'Unknown',
      percentage: mat.percentage || mat.percent || 0,
    }))

    const payload = {
      suppliers: normalizedSuppliers,
      factoryId: primaryFactoryId,
      styleRef: styleRef.trim(),
      quantityTotal,
      status,
      techPackId: techPack.id,
      // Pre-fill from TechPack
      materialComposition: materialComposition?.length ? materialComposition : undefined,
      sizeSpecifications: techPack.sizeSpecifications?.length ? techPack.sizeSpecifications : undefined,
    }

    setError('')
    createMutation.mutate(payload)
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-gradient-to-r from-violet-500 to-purple-500">
              <Package className="h-5 w-5 text-white" />
            </div>
            Create Lot from Tech Pack
          </DialogTitle>
          <DialogDescription>
            Create a new production lot using data extracted from <strong>{techPack.styleRef}</strong>
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6 py-4">
          {error && (
            <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Pre-filled Data Info */}
          <div className="bg-gradient-to-r from-violet-50 to-purple-50 border border-violet-100 rounded-lg p-4">
            <div className="flex gap-3">
              <Sparkles className="h-5 w-5 text-violet-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-violet-900">Pre-filled from Tech Pack</p>
                <ul className="text-violet-700 mt-1 space-y-1">
                  {techPack.productName && <li>Product: {techPack.productName}</li>}
                  {techPack.season && <li>Season: {techPack.season}</li>}
                  {techPack.materialComposition?.length && (
                    <li>Materials: {techPack.materialComposition.map((m: any) => m.material || m.name).join(', ')}</li>
                  )}
                  {techPack.sizeSpecifications?.length && (
                    <li>Sizes: {techPack.sizeSpecifications.length} size specifications</li>
                  )}
                </ul>
              </div>
            </div>
          </div>

          {/* Style Reference */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Style Reference</label>
            <input
              type="text"
              value={styleRef}
              onChange={(e) => setStyleRef(e.target.value)}
              className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-violet-500 focus:outline-none focus:ring-violet-500"
              placeholder="e.g. HM-SS24-001"
              required
            />
          </div>

          {/* Quantity */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Total Quantity</label>
            <input
              type="number"
              min={1}
              value={quantityTotal || ''}
              onChange={(e) => setQuantityTotal(Number(e.target.value))}
              className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-violet-500 focus:outline-none focus:ring-violet-500"
              placeholder="Total units in the lot"
              required
            />
            {(techPack.sizeSpecifications?.length ?? 0) > 0 && (
              <p className="mt-1 text-xs text-slate-500">
                Based on size specifications from tech pack
              </p>
            )}
          </div>

          {/* Status */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Initial Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as LotStatus)}
              className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-violet-500 focus:outline-none focus:ring-violet-500"
            >
              {STATUS_ORDER.map((value) => (
                <option key={value} value={value}>
                  {formatLotStatus(value)}
                </option>
              ))}
            </select>
          </div>

          {/* Supplier Factories */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Supplier Factories</label>
            {factoriesLoading ? (
              <div className="rounded-md border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                Loading factories...
              </div>
            ) : factories.length === 0 ? (
              <div className="rounded-md border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                No factories available. Add suppliers from the Factories screen first.
              </div>
            ) : (
              <div className="space-y-3 max-h-60 overflow-y-auto">
                {factories.map((factory) => {
                  const supplier = suppliers.find((s) => s.factoryId === factory.id)
                  const isSelected = Boolean(supplier)

                  const capabilityRoles = (factory.capabilities ?? [])
                    .map((cap) => cap.role ?? supplyChainRoleMap.get(cap.roleId))
                    .filter((role): role is SupplyChainRole => Boolean(role))

                  return (
                    <div
                      key={factory.id}
                      className={`rounded-md border p-3 ${
                        isSelected ? 'border-violet-300 bg-violet-50/50' : 'border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <label className="flex items-center space-x-3 text-sm font-medium text-slate-700">
                          <input
                            type="checkbox"
                            className="h-4 w-4 text-violet-600 focus:ring-violet-500"
                            checked={isSelected}
                            onChange={() => toggleSupplier(factory.id)}
                          />
                          <span>
                            {factory.name}
                            {factory.city ? ` - ${factory.city}` : ''}
                          </span>
                        </label>
                        {isSelected && (
                          <label className="flex items-center space-x-2 text-xs text-slate-600">
                            <input
                              type="radio"
                              name="primarySupplier"
                              className="h-3 w-3 text-violet-600 focus:ring-violet-500"
                              checked={supplier?.isPrimary ?? false}
                              onChange={() => setPrimarySupplier(factory.id)}
                            />
                            <span>Primary</span>
                          </label>
                        )}
                      </div>

                      {isSelected && capabilityRoles.length > 0 && (
                        <div className="mt-3 pl-7">
                          <p className="text-xs font-medium text-slate-500 mb-2">Roles:</p>
                          <div className="flex flex-wrap gap-2">
                            {capabilityRoles.map((role) => {
                              const hasRole = supplier?.roles.some((r) => r.roleId === role.id)
                              return (
                                <button
                                  key={role.id}
                                  type="button"
                                  onClick={() => toggleSupplierRole(factory.id, role.id)}
                                  className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                                    hasRole
                                      ? 'bg-violet-600 text-white'
                                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                                  }`}
                                >
                                  {role.name}
                                  {hasRole && <CheckCircle2 className="inline-block ml-1 h-3 w-3" />}
                                </button>
                              )
                            })}
                          </div>
                        </div>
                      )}

                      {isSelected && capabilityRoles.length === 0 && (
                        <p className="mt-2 pl-7 text-xs text-slate-500">
                          No roles configured for this factory.
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="secondary" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              loading={createMutation.isPending}
              className="bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700"
            >
              <Package className="h-4 w-4 mr-2" />
              Create Lot
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
