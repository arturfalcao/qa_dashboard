import { z } from 'zod';

export enum UserRole {
  OPERATOR = 'operator',
  CLIENT_ADMIN = 'client_admin',
  CLIENT_VIEWER = 'client_viewer',
}

export enum BatchStatus {
  DRAFT = 'draft',
  IN_PROGRESS = 'in_progress',
  AWAITING_APPROVAL = 'awaiting_approval',
  APPROVED = 'approved',
  REJECTED = 'rejected',
}

export enum DefectType {
  STAIN = 'stain',
  STITCHING = 'stitching',
  MISPRINT = 'misprint',
  MEASUREMENT = 'measurement',
  FABRIC_DEFECT = 'fabric_defect',
  HARDWARE_ISSUE = 'hardware_issue',
  DISCOLORATION = 'discoloration',
  TEAR_DAMAGE = 'tear_damage',
  OTHER = 'other',
}

export enum DefectSeverity {
  CRITICAL = 'critical',
  MAJOR = 'major',
  MINOR = 'minor',
}

export enum PhotoAngle {
  FRONT = 'front',
  BACK = 'back',
  SIDE_LEFT = 'side_left',
  SIDE_RIGHT = 'side_right',
  DETAIL_MACRO = 'detail_macro',
  HANGING = 'hanging',
  FLAT_LAY = 'flat_lay',
}

export enum ProcessStation {
  RECEIVING = 'receiving',
  INITIAL_INSPECTION = 'initial_inspection',
  IRONING = 'ironing',
  FOLDING = 'folding',
  QUALITY_CHECK = 'quality_check',
  PACKING = 'packing',
  FINAL_INSPECTION = 'final_inspection',
  DISPATCH = 'dispatch',
}

export enum EventType {
  DEFECT_DETECTED = 'DEFECT_DETECTED',
  BATCH_AWAITING_APPROVAL = 'BATCH_AWAITING_APPROVAL',
  BATCH_DECIDED = 'BATCH_DECIDED',
}

export enum ApprovalDecision {
  APPROVED = 'approved',
  REJECTED = 'rejected',
}

export const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export const RefreshTokenSchema = z.object({
  refreshToken: z.string().min(1),
});

export const ApprovalSchema = z.object({
  comment: z.string().optional(),
});

export const RejectSchema = z.object({
  comment: z.string().min(1, 'Comment is required for rejection'),
});

export const AnalyticsQuerySchema = z.object({
  groupBy: z.enum(['style', 'vendor']).optional(),
  range: z.enum(['last_7d', 'last_30d']).default('last_7d'),
});

export const ThroughputQuerySchema = z.object({
  bucket: z.enum(['day', 'week']).default('day'),
  range: z.enum(['last_7d', 'last_30d']).default('last_7d'),
});

export const ExportQuerySchema = z.object({
  batchId: z.string().uuid().optional(),
  range: z.enum(['last_7d', 'last_30d']).optional(),
});

export type LoginDto = z.infer<typeof LoginSchema>;
export type RefreshTokenDto = z.infer<typeof RefreshTokenSchema>;
export type ApprovalDto = z.infer<typeof ApprovalSchema>;
export type RejectDto = z.infer<typeof RejectSchema>;
export type AnalyticsQuery = z.infer<typeof AnalyticsQuerySchema>;
export type ThroughputQuery = z.infer<typeof ThroughputQuerySchema>;
export type ExportQuery = z.infer<typeof ExportQuerySchema>;

export interface User {
  id: string;
  tenantId: string;
  email: string;
  role: UserRole;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  createdAt: string;
  updatedAt: string;
}

export interface Vendor {
  id: string;
  tenantId: string;
  name: string;
  code: string;
  createdAt: string;
  updatedAt: string;
}

export interface Style {
  id: string;
  tenantId: string;
  styleCode: string;
  description: string;
  createdAt: string;
  updatedAt: string;
}

export interface ProcessStationProgress {
  station: ProcessStation;
  startedAt?: string;
  completedAt?: string;
  assignedWorker?: string;
  notes?: string;
  qualityScore?: number;
}

export interface Batch {
  id: string;
  tenantId: string;
  vendorId: string;
  styleId: string;
  poNumber: string;
  quantity: number;
  status: BatchStatus;
  currentStation: ProcessStation;
  processProgress: ProcessStationProgress[];
  estimatedCompletionTime?: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  createdAt: string;
  updatedAt: string;
  vendor?: Vendor;
  style?: Style;
  approvals?: Approval[];
  _count?: {
    garments: number;
    inspections: number;
    defects: number;
    completedStations: number;
  };
}

export interface Garment {
  id: string;
  tenantId: string;
  batchId: string;
  serial: string;
  size: string;
  color: string;
  createdAt: string;
  updatedAt: string;
}

export interface PhotoAnnotation {
  id: string;
  x: number; // X coordinate as percentage
  y: number; // Y coordinate as percentage
  comment: string;
  defectType?: DefectType;
  severity?: DefectSeverity;
  createdBy: string;
  createdAt: string;
}

export interface InspectionPhoto {
  id: string;
  angle: PhotoAngle;
  photoKey: string;
  photoUrl?: string;
  annotations: PhotoAnnotation[];
  capturedAt: string;
}

export interface Inspection {
  id: string;
  tenantId: string;
  garmentId: string;
  hasDefect: boolean;
  defectType?: DefectType;
  defectSeverity?: DefectSeverity;
  notes?: string;
  photoKeyBefore?: string; // Deprecated - keeping for backward compatibility
  photoKeyAfter?: string;  // Deprecated - keeping for backward compatibility
  photos: InspectionPhoto[]; // New multi-angle photo system
  processStation: ProcessStation;
  assignedWorker?: string;
  environmentalConditions?: {
    temperature: number;
    humidity: number;
    lightingLevel: number;
  };
  qualityScore?: number; // 0-100 quality score
  inspectedAt: string;
  createdAt: string;
  updatedAt: string;
  garment?: Garment & { batch?: Batch & { vendor?: Vendor; style?: Style } };
  photoUrlBefore?: string; // Deprecated - keeping for backward compatibility
  photoUrlAfter?: string;  // Deprecated - keeping for backward compatibility
}

export interface Approval {
  id: string;
  tenantId: string;
  batchId: string;
  decidedBy: string;
  decision: ApprovalDecision;
  comment?: string;
  decidedAt: string;
  createdAt: string;
  updatedAt: string;
  user?: User;
}

export interface Event {
  id: string;
  tenantId: string;
  type: EventType;
  payload: any;
  createdAt: string;
}

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  user: User;
}

export interface DefectRateAnalytics {
  groupBy?: 'style' | 'vendor';
  data: Array<{
    name: string;
    defectRate: number;
    totalInspected: number;
    totalDefects: number;
  }>;
}

export interface ThroughputAnalytics {
  data: Array<{
    date: string;
    inspections: number;
  }>;
}

export interface DefectTypeAnalytics {
  data: Array<{
    type: DefectType;
    count: number;
    percentage: number;
  }>;
}

export interface ApprovalTimeAnalytics {
  average: number;
  p50: number;
  p90: number;
}