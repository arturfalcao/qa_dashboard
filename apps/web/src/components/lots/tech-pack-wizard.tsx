'use client'

import { useState, useCallback, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { LotStatus } from '@qa-dashboard/shared'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectOption } from '@/components/ui/select'
import {
  Upload,
  FileText,
  CheckCircle,
  AlertCircle,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Package,
  Factory,
  Sparkles,
  Zap,
  FileImage,
  FileSpreadsheet,
  Palette,
  Ruler,
  Shield,
  Droplets,
  Hash,
  Calendar,
  Building2,
  Shirt,
  ScanLine,
  Wand2,
  ArrowRight
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface TechPackWizardProps {
  isOpen: boolean
  onClose: () => void
  tenantSlug: string
}

const WIZARD_STEPS = [
  { id: 'upload', title: 'Upload Tech Pack', icon: Upload, gradient: 'from-violet-500 to-purple-600' },
  { id: 'review', title: 'AI Review', icon: Wand2, gradient: 'from-blue-500 to-cyan-600' },
  { id: 'factory', title: 'Select Factory', icon: Factory, gradient: 'from-emerald-500 to-green-600' },
  { id: 'confirm', title: 'Create Magic', icon: Sparkles, gradient: 'from-amber-500 to-orange-600' },
]

// Simple label component
const Label = ({ children, htmlFor, className = '' }: { children: React.ReactNode; htmlFor?: string; className?: string }) => (
  <label htmlFor={htmlFor} className={cn("text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70", className)}>
    {children}
  </label>
)

export function TechPackWizard({ isOpen, onClose, tenantSlug }: TechPackWizardProps) {
  const router = useRouter()
  const queryClient = useQueryClient()

  const [currentStep, setCurrentStep] = useState(0)
  const [techPackFile, setTechPackFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [extractedData, setExtractedData] = useState<any>(null)
  const [formData, setFormData] = useState({
    styleRef: '',
    productName: '',
    quantityTotal: 0,
    suppliers: [] as Array<{ factoryId: string; isPrimary?: boolean; stage?: string }>,
    materialComposition: [] as any[],
    dyeLot: '',
    colors: [] as any[],
    sizeSpecifications: [] as any[],
    certifications: [] as any[],
    washCareInstructions: [] as string[],
  })

  // Fetch factories for selection
  const { data: factories = [] } = useQuery({
    queryKey: ['factories'],
    queryFn: apiClient.getFactories,
  })

  // Create lot mutation
  const createLotMutation = useMutation({
    mutationFn: async (data: any) => {
      // Transform material composition to API format
      const materialComposition = data.materialComposition
        ?.filter((m: any) => m.fiber && typeof m.percentage === 'number')
        .map((m: any) => ({
          fiber: m.fiber,
          percentage: m.percentage,
          properties: m.properties,
        }))

      // Transform certifications to API format
      const certifications = data.certifications
        ?.filter((c: any) => typeof c === 'object' && c.type)
        .map((c: any) => ({
          type: c.type,
          number: c.number,
          auditLink: c.auditLink,
          validUntil: c.validUntil,
          issuer: c.issuer,
        }))

      const lotData = {
        styleRef: data.styleRef,
        quantityTotal: data.quantityTotal,
        ...(data.suppliers && data.suppliers.length > 0 ? { suppliers: data.suppliers } : {}),
        status: LotStatus.PLANNED,
        ...(materialComposition && materialComposition.length > 0 ? { materialComposition } : {}),
        ...(data.dyeLot ? { dyeLot: data.dyeLot } : {}),
        ...(certifications && certifications.length > 0 ? { certifications } : {}),
      }

      // Create the lot
      const createdLot = await apiClient.createLot(lotData)

      // Upload the tech pack file to the created lot if we have one
      if (techPackFile) {
        await apiClient.uploadTechPack(createdLot.id, techPackFile)
      }

      return createdLot
    },
    onSuccess: (lot) => {
      console.log('Lot created successfully from tech pack')
      queryClient.invalidateQueries({ queryKey: ['lots'] })
      onClose()
      router.push(`/c/${tenantSlug}/lots/${lot.id}`)
    },
    onError: (error: any) => {
      console.error('Failed to create lot:', error.message || 'Failed to create lot')
      alert(`Error: ${error.message || 'Failed to create lot'}`)
    },
  })

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      const allowedTypes = [
        'application/pdf',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv',
        'image/jpeg',
        'image/png',
        'text/plain',
      ]

      if (!allowedTypes.includes(file.type)) {
        alert('Invalid file type. Please upload PDF, Excel, CSV, or image files')
        return
      }

      setTechPackFile(file)
    }
  }

  const uploadAndExtractTechPack = async () => {
    if (!techPackFile) return

    setIsUploading(true)
    try {
      // Create a temporary lot first to upload the tech pack
      const tempLot = await apiClient.createLot({
        styleRef: 'TEMP-' + Date.now(),
        quantityTotal: 1,
        suppliers: factories[0]?.id ? [{ factoryId: factories[0].id, isPrimary: true }] : [],
        status: LotStatus.PLANNED,
      })

      // Upload tech pack to the temporary lot
      const uploadResult = await apiClient.uploadTechPack(tempLot.id, techPackFile)

      // Extract the data
      if (uploadResult.extractedData) {
        const data = uploadResult.extractedData.rawExtractedData || uploadResult.extractedData
        setExtractedData(data)

        // Pre-fill form with extracted data
        setFormData({
          styleRef: data.styleReference || data.styleRef || '',
          productName: data.productName || '',
          quantityTotal: data.productionQuantity || 0,
          suppliers: [],
          materialComposition: data.materialComposition || [],
          dyeLot: data.dyeLot || '',
          colors: data.colors || [],
          sizeSpecifications: data.sizeSpecifications || [],
          certifications: data.certifications || [],
          washCareInstructions: data.washCareInstructions || [],
        })

        // Delete the temporary lot (the tech pack file will be re-uploaded to the final lot)
        await apiClient.deleteLot(tempLot.id).catch(() => {})

        // Move to next step
        setCurrentStep(1)
      }
    } catch (error: any) {
      console.error('Extraction failed:', error)
      alert(`Failed to extract tech pack data: ${error.message || 'Unknown error'}`)
    } finally {
      setIsUploading(false)
    }
  }

  const handleNext = async () => {
    if (currentStep === 0 && techPackFile) {
      await uploadAndExtractTechPack()
    } else if (currentStep === WIZARD_STEPS.length - 1) {
      // Create the lot
      createLotMutation.mutate(formData)
    } else {
      setCurrentStep(prev => Math.min(prev + 1, WIZARD_STEPS.length - 1))
    }
  }

  const handleBack = () => {
    setCurrentStep(prev => Math.max(prev - 1, 0))
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Upload
        return (
          <div className="space-y-6">
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-50 via-purple-50 to-pink-50 border border-purple-200 p-8">
              <div className="absolute top-0 right-0 -mt-4 -mr-4 h-24 w-24 rounded-full bg-gradient-to-br from-violet-400 to-purple-600 opacity-10 blur-2xl"></div>
              <div className="absolute bottom-0 left-0 -mb-4 -ml-4 h-32 w-32 rounded-full bg-gradient-to-tr from-blue-400 to-cyan-600 opacity-10 blur-2xl"></div>

              {techPackFile ? (
                <div className="relative space-y-6">
                  <div className="mx-auto h-20 w-20 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 p-0.5 shadow-xl">
                    <div className="flex h-full w-full items-center justify-center rounded-2xl bg-white">
                      <FileText className="h-10 w-10 text-violet-600" />
                    </div>
                  </div>
                  <div className="space-y-2 text-center">
                    <p className="text-lg font-semibold text-gray-900">{techPackFile.name}</p>
                    <div className="flex items-center justify-center gap-3 text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <FileImage className="h-4 w-4" />
                        {(techPackFile.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                      <span className="flex items-center gap-1">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        Ready to Process
                      </span>
                    </div>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setTechPackFile(null)}
                    className="mx-auto flex items-center gap-2"
                  >
                    <Upload className="h-4 w-4" />
                    Choose Different File
                  </Button>
                </div>
              ) : (
                <div className="relative space-y-6 text-center">
                  <div className="mx-auto h-24 w-24 rounded-3xl bg-gradient-to-br from-violet-100 to-purple-200 p-1 animate-pulse">
                    <div className="flex h-full w-full items-center justify-center rounded-3xl bg-white">
                      <Upload className="h-12 w-12 text-violet-500" />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <p className="text-xl font-bold bg-gradient-to-r from-violet-600 to-purple-600 bg-clip-text text-transparent">
                      Drop Your Tech Pack Here
                    </p>
                    <p className="text-sm text-gray-600">
                      or click to browse files
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 justify-center">
                    <span className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-700 shadow-sm">
                      <FileText className="h-3 w-3" /> PDF
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-700 shadow-sm">
                      <FileSpreadsheet className="h-3 w-3" /> Excel
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-700 shadow-sm">
                      <FileImage className="h-3 w-3" /> Images
                    </span>
                  </div>
                  <label className="relative inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-violet-600 to-purple-600 px-8 py-3 text-sm font-semibold text-white shadow-lg hover:shadow-xl transition-all cursor-pointer group">
                    <Wand2 className="h-4 w-4 group-hover:rotate-12 transition-transform" />
                    Select Tech Pack
                    <Sparkles className="h-4 w-4 absolute -top-1 -right-1 text-yellow-300 animate-pulse" />
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.xlsx,.xls,.csv,.jpg,.jpeg,.png,.txt"
                      onChange={handleFileSelect}
                    />
                  </label>
                </div>
              )}
            </div>

            <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 p-[1px]">
              <div className="rounded-xl bg-white p-4">
                <div className="flex gap-3">
                  <div className="flex-shrink-0">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-cyan-500">
                      <Zap className="h-5 w-5 text-white" />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <p className="font-semibold text-gray-900">AI Magic Extraction</p>
                    <p className="text-sm text-gray-600">
                      Our AI instantly extracts style codes, materials, measurements, colors, and certifications from any tech pack format
                    </p>
                    <div className="flex flex-wrap gap-2 pt-2">
                      <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                        <Hash className="h-3 w-3" /> Style Ref
                      </span>
                      <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                        <Shirt className="h-3 w-3" /> Materials
                      </span>
                      <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                        <Ruler className="h-3 w-3" /> Sizes
                      </span>
                      <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                        <Palette className="h-3 w-3" /> Colors
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )

      case 1: // Review
        return (
          <div className="space-y-6 max-h-[450px] overflow-y-auto pr-2">
            <div className="rounded-xl bg-gradient-to-br from-blue-50 to-cyan-50 p-4 border border-blue-200">
              <div className="flex items-center gap-2 mb-3">
                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                  <Wand2 className="h-4 w-4 text-white" />
                </div>
                <p className="font-semibold text-gray-900">AI Extracted Data</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="styleRef" className="flex items-center gap-2">
                    <Hash className="h-3 w-3 text-gray-500" />
                    Style Reference
                  </Label>
                  <Input
                    id="styleRef"
                    value={formData.styleRef}
                    onChange={(e) => setFormData(prev => ({ ...prev, styleRef: e.target.value }))}
                    placeholder="e.g., WJ2024-001"
                    className="bg-white/80 backdrop-blur-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="productName" className="flex items-center gap-2">
                    <Shirt className="h-3 w-3 text-gray-500" />
                    Product Name
                  </Label>
                  <Input
                    id="productName"
                    value={formData.productName}
                    onChange={(e) => setFormData(prev => ({ ...prev, productName: e.target.value }))}
                    placeholder="e.g., Cotton T-Shirt"
                    className="bg-white/80 backdrop-blur-sm"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="quantity">Production Quantity</Label>
                <Input
                  id="quantity"
                  type="number"
                  value={formData.quantityTotal}
                  onChange={(e) => setFormData(prev => ({ ...prev, quantityTotal: parseInt(e.target.value) || 0 }))}
                />
              </div>
              <div>
                <Label htmlFor="dyeLot">Dye Lot</Label>
                <Input
                  id="dyeLot"
                  value={formData.dyeLot}
                  onChange={(e) => setFormData(prev => ({ ...prev, dyeLot: e.target.value }))}
                  placeholder="e.g., DL-2024-0315"
                />
              </div>
            </div>

            {formData.materialComposition.length > 0 && (
              <div>
                <Label>Material Composition</Label>
                <div className="bg-gray-50 rounded-lg p-3 mt-1 space-y-1">
                  {formData.materialComposition.map((material, index) => (
                    <div key={index} className="text-sm">
                      <span className="font-medium">{material.component || 'Material'}:</span>{' '}
                      {material.composition || `${material.fiber} ${material.percentage}%`}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {formData.colors.length > 0 && (
              <div>
                <Label>Colors</Label>
                <div className="flex flex-wrap gap-2 mt-1">
                  {formData.colors.map((color, index) => (
                    <div key={index} className="bg-gray-100 rounded px-3 py-1 text-sm">
                      {color.name}
                      {color.pantone && (
                        <span className="text-gray-500 text-xs ml-1">({color.pantone})</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {formData.sizeSpecifications.length > 0 && (
              <div>
                <Label>Size Specifications</Label>
                <div className="bg-gray-50 rounded-lg p-3 mt-1">
                  <div className="grid grid-cols-5 gap-2 text-xs font-medium text-gray-600 mb-2">
                    <div>Size</div>
                    <div>Chest</div>
                    <div>Length</div>
                    <div>Sleeve</div>
                    <div>Shoulder</div>
                  </div>
                  {formData.sizeSpecifications.map((spec, index) => (
                    <div key={index} className="grid grid-cols-5 gap-2 text-sm">
                      <div className="font-medium">{spec.size}</div>
                      <div>{spec.measurements?.chest || '-'}</div>
                      <div>{spec.measurements?.length || '-'}</div>
                      <div>{spec.measurements?.sleeve || '-'}</div>
                      <div>{spec.measurements?.shoulder || '-'}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )

      case 2: // Factory
        return (
          <div className="space-y-6">
            <div>
              <Label>Select Factories</Label>
              <p className="text-xs text-gray-500 mt-1 mb-3">Choose one or more factories for this lot</p>

              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {factories.map((factory: any) => {
                  const isSelected = formData.suppliers.some(s => s.factoryId === factory.id)
                  return (
                    <div
                      key={factory.id}
                      onClick={() => {
                        setFormData(prev => {
                          const exists = prev.suppliers.some(s => s.factoryId === factory.id)
                          if (exists) {
                            return {
                              ...prev,
                              suppliers: prev.suppliers.filter(s => s.factoryId !== factory.id)
                            }
                          } else {
                            return {
                              ...prev,
                              suppliers: [
                                ...prev.suppliers,
                                {
                                  factoryId: factory.id,
                                  isPrimary: prev.suppliers.length === 0,
                                }
                              ]
                            }
                          }
                        })
                      }}
                      className={cn(
                        "cursor-pointer rounded-lg border-2 p-4 transition-all",
                        isSelected
                          ? "border-violet-500 bg-violet-50"
                          : "border-gray-200 hover:border-gray-300 bg-white"
                      )}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-gray-900">{factory.name}</p>
                            {isSelected && formData.suppliers.find(s => s.factoryId === factory.id)?.isPrimary && (
                              <span className="inline-flex items-center rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700">
                                Primary
                              </span>
                            )}
                          </div>
                          {factory.city && (
                            <p className="text-sm text-gray-500 mt-1">
                              {factory.city}, {factory.country}
                            </p>
                          )}
                        </div>
                        <div className={cn(
                          "h-5 w-5 rounded border-2 flex items-center justify-center",
                          isSelected ? "bg-violet-500 border-violet-500" : "border-gray-300"
                        )}>
                          {isSelected && <CheckCircle className="h-4 w-4 text-white" />}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {formData.suppliers.length > 0 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">
                  Selected: {formData.suppliers.length} {formData.suppliers.length === 1 ? 'Factory' : 'Factories'}
                </h4>
                <div className="space-y-2">
                  {formData.suppliers.map((supplier, idx) => {
                    const factory = factories.find((f: any) => f.id === supplier.factoryId)
                    return factory ? (
                      <div key={idx} className="flex items-center justify-between text-sm">
                        <span className="text-gray-700">{factory.name}</span>
                        {supplier.isPrimary && (
                          <span className="text-xs text-violet-600 font-medium">Primary</span>
                        )}
                      </div>
                    ) : null
                  })}
                </div>
              </div>
            )}
          </div>
        )

      case 3: // Confirm
        return (
          <div className="space-y-6">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex">
                <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 mr-2 flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-medium text-green-900">Ready to Create Lot</p>
                  <p className="text-green-700 mt-1">
                    Review the summary below and click &quot;Create Lot&quot; to finish
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex justify-between py-2 border-b">
                <span className="text-sm text-gray-500">Style Reference</span>
                <span className="text-sm font-medium">{formData.styleRef}</span>
              </div>
              {formData.productName && (
                <div className="flex justify-between py-2 border-b">
                  <span className="text-sm text-gray-500">Product</span>
                  <span className="text-sm font-medium">{formData.productName}</span>
                </div>
              )}
              <div className="flex justify-between py-2 border-b">
                <span className="text-sm text-gray-500">Quantity</span>
                <span className="text-sm font-medium">{formData.quantityTotal.toLocaleString()} units</span>
              </div>
              <div className="flex justify-between py-2 border-b">
                <span className="text-sm text-gray-500">Factories</span>
                <span className="text-sm font-medium">
                  {formData.suppliers.length} selected
                </span>
              </div>
              {formData.materialComposition.length > 0 && (
                <div className="flex justify-between py-2 border-b">
                  <span className="text-sm text-gray-500">Materials</span>
                  <span className="text-sm font-medium">{formData.materialComposition.length} components</span>
                </div>
              )}
              {formData.colors.length > 0 && (
                <div className="flex justify-between py-2 border-b">
                  <span className="text-sm text-gray-500">Colors</span>
                  <span className="text-sm font-medium">{formData.colors.length} variants</span>
                </div>
              )}
              {formData.sizeSpecifications.length > 0 && (
                <div className="flex justify-between py-2">
                  <span className="text-sm text-gray-500">Sizes</span>
                  <span className="text-sm font-medium">{formData.sizeSpecifications.length} sizes</span>
                </div>
              )}
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-br from-violet-600 via-purple-600 to-pink-600 opacity-5"></div>
        <DialogHeader className="relative">
          <div className="flex items-center gap-3 mb-2">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <DialogTitle className="text-xl font-bold">
                <span className="bg-gradient-to-r from-violet-600 to-purple-600 bg-clip-text text-transparent">
                  Tech Pack Magic ✨
                </span>
              </DialogTitle>
              <DialogDescription>
                Upload your tech pack and watch AI extract everything automatically
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Progress Steps */}
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t-2 border-gray-100"></div>
          </div>
          <div className="relative flex items-center justify-between">
            {WIZARD_STEPS.map((step, index) => {
              const Icon = step.icon
              const isActive = index === currentStep
              const isCompleted = index < currentStep

              return (
                <div key={step.id} className="flex flex-col items-center">
                  <div className="relative">
                    {isActive && (
                      <div className={cn(
                        "absolute inset-0 rounded-full opacity-20 blur-xl animate-pulse",
                        isActive && index === 0 && "bg-gradient-to-r from-violet-500 to-purple-600",
                        isActive && index === 1 && "bg-gradient-to-r from-blue-500 to-cyan-600",
                        isActive && index === 2 && "bg-gradient-to-r from-emerald-500 to-green-600",
                        isActive && index === 3 && "bg-gradient-to-r from-amber-500 to-orange-600"
                      )}>
                      </div>
                    )}
                    <div
                      className={cn(
                        "relative w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300 transform",
                        isActive && index === 0 && "bg-gradient-to-br from-violet-500 to-purple-600 text-white shadow-xl scale-110",
                        isActive && index === 1 && "bg-gradient-to-br from-blue-500 to-cyan-600 text-white shadow-xl scale-110",
                        isActive && index === 2 && "bg-gradient-to-br from-emerald-500 to-green-600 text-white shadow-xl scale-110",
                        isActive && index === 3 && "bg-gradient-to-br from-amber-500 to-orange-600 text-white shadow-xl scale-110",
                        isCompleted && "bg-gradient-to-br from-green-500 to-emerald-600 text-white shadow-lg",
                        !isActive && !isCompleted && "bg-gray-100 text-gray-400"
                      )}
                    >
                      {isCompleted ? (
                        <CheckCircle className="w-6 h-6" />
                      ) : (
                        <Icon className={cn("w-6 h-6", isActive && "animate-pulse")} />
                      )}
                    </div>
                    {index < WIZARD_STEPS.length - 1 && (
                      <div className={cn(
                        "absolute top-7 left-14 w-[calc(100vw/5)] h-1 transition-all duration-500",
                        isCompleted ? "bg-gradient-to-r from-green-500 to-emerald-500" : "bg-gray-100"
                      )} />
                    )}
                  </div>
                  <div className="mt-2 text-center">
                    <p className={cn(
                      "text-xs font-semibold transition-colors",
                      (isActive || isCompleted) ? "text-gray-900" : "text-gray-400"
                    )}>
                      {step.title}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Step Content */}
        <div className="min-h-[300px]">
          {renderStepContent()}
        </div>

        <DialogFooter className="relative">
          <div className="absolute inset-0 bg-gradient-to-t from-gray-50 to-transparent opacity-50 pointer-events-none"></div>
          <div className="relative flex justify-between w-full">
            <Button
              variant="secondary"
              onClick={handleBack}
              disabled={currentStep === 0 || isUploading || createLotMutation.isPending}
              className="group"
            >
              <ChevronLeft className="w-4 h-4 mr-1 group-hover:-translate-x-1 transition-transform" />
              Back
            </Button>

            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={onClose}
                disabled={isUploading || createLotMutation.isPending}
              >
                Cancel
              </Button>

              <Button
                onClick={handleNext}
                disabled={
                  (currentStep === 0 && !techPackFile) ||
                  (currentStep === 2 && formData.suppliers.length === 0) ||
                  isUploading ||
                  createLotMutation.isPending
                }
                className={cn(
                  "relative group overflow-hidden transition-all duration-300",
                  currentStep === WIZARD_STEPS.length - 1
                    ? "bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white px-6 shadow-lg hover:shadow-xl transform hover:scale-105"
                    : isUploading
                    ? "bg-gradient-to-r from-violet-600 to-purple-600"
                    : "bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white"
                )}
              >
                <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 transition-opacity"></div>
                <div className="relative flex items-center">
                  {isUploading || createLotMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      <span>{currentStep === 0 ? 'Extracting Magic...' : 'Creating...'}</span>
                    </>
                  ) : currentStep === WIZARD_STEPS.length - 1 ? (
                    <>
                      <Wand2 className="w-4 h-4 mr-2 group-hover:rotate-12 transition-transform" />
                      <span className="font-semibold">Create Lot</span>
                      <Sparkles className="w-4 h-4 ml-2 text-yellow-300 animate-pulse" />
                    </>
                  ) : (
                    <>
                      <span>Next</span>
                      <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                    </>
                  )}
                </div>
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}