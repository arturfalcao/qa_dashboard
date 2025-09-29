import { ReportType, ReportLanguage, ReportStatus } from '@qa-dashboard/shared';

export interface ReportGenerationRequest {
  type: ReportType;
  tenantId: string;
  userId?: string;
  language?: ReportLanguage;
  parameters: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface ReportGenerationResult {
  id: string;
  type: ReportType;
  status: ReportStatus;
  fileName: string;
  url?: string;
  filePath?: string;
  size?: number;
  generatedAt?: Date;
  expiresAt?: Date;
  error?: string;
  metadata?: Record<string, any>;
}

// Report-specific parameter interfaces
export interface ExecutiveQualitySummaryParams {
  period: {
    startDate: string;
    endDate: string;
  };
  purchaseOrders?: string[];
  styles?: string[];
}

export interface LotInspectionReportParams {
  lotId: string;
  includePhotos?: boolean;
  includeDefectDetails?: boolean;
}

export interface MeasurementComplianceSheetParams {
  lotId: string;
  sampleIds?: string[];
  includeMeasurementImages?: boolean;
}

export interface PackagingReadinessReportParams {
  lotId: string;
  includePackagingPhotos?: boolean;
  includeShippingLabels?: boolean;
}

export interface SupplierPerformanceSnapshotParams {
  period: {
    startDate: string;
    endDate: string;
  };
  supplierIds?: string[];
  includeComparison?: boolean;
}

export interface CapaReportParams {
  capaId: string;
  includeEvidence?: boolean;
  includeTimeline?: boolean;
}

export interface InlineQcCheckpointsParams {
  lotId: string;
  phase?: string;
  includePhotos?: boolean;
}

export interface DppSummaryParams {
  dppId?: string;
  lotId?: string;
  purchaseOrderNumber?: string;
}

// Report data interfaces for templates
export interface ExecutiveQualitySummaryData {
  client: {
    name: string;
    logo?: string;
  };
  period: {
    startDate: string;
    endDate: string;
  };
  kpis: {
    averageDefectRate: number;
    firstPassYield: number;
    averageLeadTime: number;
  };
  topDefects: Array<{
    name: string;
    count: number;
    percentage: number;
  }>;
  supplierPerformance: Array<{
    name: string;
    defectRate: number;
    performance: 'good' | 'average' | 'poor';
  }>;
  insights: string[];
  coverageStats: {
    purchaseOrders: number;
    styles: number;
    totalQuantity: number;
  };
}

export interface LotInspectionReportData {
  lot: {
    id: string;
    styleRef: string;
    quantity: number;
    factory: {
      name: string;
      location: string;
    };
  };
  inspection: {
    date: string;
    inspector: string;
    duration: number;
    status: string;
  };
  defects: Array<{
    type: string;
    count: number;
    severity: 'critical' | 'major' | 'minor';
    images?: string[];
  }>;
  measurements?: Array<{
    point: string;
    specification: string;
    tolerance: string;
    measured: string;
    deviation: number;
    status: 'pass' | 'fail';
  }>;
  photos: Array<{
    url: string;
    caption: string;
    annotations?: any[];
  }>;
  decision: 'approved' | 'correction_required' | 'rejected';
  comments?: string;
}

export interface MeasurementComplianceSheetData {
  lot: {
    id: string;
    styleRef: string;
    quantity: number;
    factory: {
      name: string;
      location: string;
    };
  };
  inspection: {
    date: string;
    inspector: string;
    status: string;
  };
  measurements: Array<{
    sampleId?: string;
    measurementPoint: string;
    specification: {
      target: string;
      tolerance: string;
      unit: string;
    };
    measured: {
      value: string;
      unit: string;
    };
    deviation: number;
    status: 'pass' | 'fail';
    notes?: string;
    images?: string[];
  }>;
  summary: {
    totalMeasurements: number;
    passedMeasurements: number;
    failedMeasurements: number;
    overallCompliance: number;
  };
  approvalStatus: 'approved' | 'conditional' | 'rejected';
  comments?: string;
}

export interface PackagingReadinessReportData {
  lot: {
    id: string;
    styleRef: string;
    quantity: number;
    factory: {
      name: string;
      location: string;
    };
  };
  inspection: {
    date: string;
    inspector: string;
    status: string;
  };
  packaging: {
    status: 'ready' | 'pending' | 'issues';
    completedChecks: number;
    totalChecks: number;
    completionPercentage: number;
    readinessDate?: string;
  };
  checklist: Array<{
    category: string;
    items: Array<{
      name: string;
      status: 'completed' | 'pending' | 'failed';
      notes?: string;
      checkedBy?: string;
      checkedAt?: string;
    }>;
  }>;
  packagingPhotos: Array<{
    url: string;
    caption: string;
    category: 'packaging' | 'labeling' | 'shipping_prep' | 'quality_control';
    takenAt?: string;
  }>;
  shippingLabels: Array<{
    type: 'main_label' | 'care_label' | 'size_label' | 'barcode';
    status: 'approved' | 'pending' | 'rejected';
    url?: string;
    notes?: string;
  }>;
  qualityChecks: Array<{
    checkType: string;
    result: 'pass' | 'fail' | 'conditional';
    details?: string;
    inspector?: string;
    checkedAt?: string;
  }>;
  finalApproval: 'approved' | 'conditional' | 'rejected';
  shipmentReadiness: {
    estimatedShipDate?: string;
    actualShipDate?: string;
    carrier?: string;
    trackingNumber?: string;
  };
  comments?: string;
}

export interface DppSummaryReportData {
  dpp: {
    id: string;
    lotId?: string;
    purchaseOrderNumber?: string;
    status: 'draft' | 'published' | 'archived';
    version: string;
    publishedAt?: string;
    expiresAt?: string;
  };
  product: {
    name: string;
    styleRef: string;
    description: string;
    category: string;
    season: string;
    composition: Array<{
      material: string;
      percentage: number;
      origin?: string;
      certifications?: string[];
    }>;
    care: {
      washingTemp: number;
      dryingMethod: string;
      ironingTemp: string;
      specialCare?: string[];
    };
  };
  sustainability: {
    carbonFootprint: {
      total: number;
      unit: 'kg CO2e';
      breakdown: Array<{
        stage: string;
        amount: number;
        percentage: number;
      }>;
    };
    waterUsage: {
      total: number;
      unit: 'liters';
      breakdown: Array<{
        stage: string;
        amount: number;
        percentage: number;
      }>;
    };
    recyclability: {
      percentage: number;
      methods: string[];
      instructions: string;
    };
    certifications: Array<{
      name: string;
      issuer: string;
      validFrom: string;
      validTo: string;
      certificateNumber: string;
    }>;
  };
  supplyChain: {
    suppliers: Array<{
      name: string;
      role: string;
      location: string;
      tier: number;
      certifications: string[];
      sustainabilityScore: number;
    }>;
    totalSuppliers: number;
    geographicSpread: Array<{
      country: string;
      percentage: number;
    }>;
  };
  compliance: {
    regulations: Array<{
      name: string;
      region: string;
      status: 'compliant' | 'pending' | 'non-compliant';
      validatedAt?: string;
      notes?: string;
    }>;
    testResults: Array<{
      testType: string;
      standard: string;
      result: 'pass' | 'fail';
      testedAt: string;
      laboratory: string;
      certificateNumber: string;
    }>;
  };
  traceability: {
    batchNumber: string;
    productionDate: string;
    factoryLocation: string;
    rawMaterialOrigins: Array<{
      material: string;
      origin: string;
      supplier: string;
      harvestDate?: string;
    }>;
    productionSteps: Array<{
      step: string;
      location: string;
      supplier: string;
      completedAt: string;
      co2Impact: number;
    }>;
  };
  circularity: {
    designForCircularity: {
      score: number;
      maxScore: number;
      factors: Array<{
        factor: string;
        score: number;
        maxScore: number;
        description: string;
      }>;
    };
    repairability: {
      score: number;
      instructions: string[];
      spareParts: string[];
    };
    endOfLife: {
      options: Array<{
        method: string;
        description: string;
        environmentalImpact: string;
      }>;
      recommendations: string[];
    };
  };
  accessibilityInfo: {
    qrCode?: string;
    nfcEnabled?: boolean;
    digitalTwinUrl?: string;
    mobileAppDeeplink?: string;
    supportedLanguages: string[];
  };
}