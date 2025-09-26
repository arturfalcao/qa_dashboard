import { z } from "zod";

export enum UserRole {
  ADMIN = "ADMIN",
  OPS_MANAGER = "OPS_MANAGER",
  INSPECTOR = "INSPECTOR",
  CLIENT_VIEWER = "CLIENT_VIEWER",
  CLEVEL = "CLEVEL",
}

export enum FactoryCertificationType {
  GOTS = "GOTS",
  OEKO_TEX_STANDARD_100 = "OEKO_TEX_STANDARD_100",
  GRS = "GRS",
  RCS = "RCS",
  ISO_14001 = "ISO_14001",
  BLUESIGN = "BLUESIGN",
  AMFORI_BSCI = "AMFORI_BSCI",
}

export enum LotStatus {
  PLANNED = "PLANNED",
  IN_PRODUCTION = "IN_PRODUCTION",
  INSPECTION = "INSPECTION",
  PENDING_APPROVAL = "PENDING_APPROVAL",
  APPROVED = "APPROVED",
  REJECTED = "REJECTED",
  SHIPPED = "SHIPPED",
}

export enum ApprovalDecision {
  APPROVE = "APPROVE",
  REJECT = "REJECT",
}

export enum ReportType {
  MONTHLY_SCORECARD = "MONTHLY_SCORECARD",
  LOT = "LOT",
  EXECUTIVE_QUALITY_SUMMARY = "EXECUTIVE_QUALITY_SUMMARY",
  LOT_INSPECTION_REPORT = "LOT_INSPECTION_REPORT",
  MEASUREMENT_COMPLIANCE_SHEET = "MEASUREMENT_COMPLIANCE_SHEET",
  PACKAGING_READINESS_REPORT = "PACKAGING_READINESS_REPORT",
  SUPPLIER_PERFORMANCE_SNAPSHOT = "SUPPLIER_PERFORMANCE_SNAPSHOT",
  CAPA_REPORT = "CAPA_REPORT",
  INLINE_QC_CHECKPOINTS = "INLINE_QC_CHECKPOINTS",
  DPP_SUMMARY = "DPP_SUMMARY",
}

export enum ReportStatus {
  PENDING = "PENDING",
  READY = "READY",
  FAILED = "FAILED",
  GENERATING = "GENERATING",
  COMPLETED = "COMPLETED",
  EXPIRED = "EXPIRED",
}

export enum ReportLanguage {
  PT = "PT",
  EN = "EN",
  ES = "ES",
}

export enum SupplyChainStageStatus {
  NOT_STARTED = "NOT_STARTED",
  IN_PROGRESS = "IN_PROGRESS",
  COMPLETED = "COMPLETED",
}

export enum EventType {
  DEFECT_DETECTED = "DEFECT_DETECTED",
  LOT_AWAITING_APPROVAL = "LOT_AWAITING_APPROVAL",
  LOT_DECIDED = "LOT_DECIDED",
}

export const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export const RefreshTokenSchema = z.object({
  refreshToken: z.string().min(1),
});

export const ApprovalSchema = z.object({
  note: z.string().optional(),
});

export const RejectSchema = z.object({
  note: z.string().min(1, "Note is required when rejecting a lot"),
});

export const ExportQuerySchema = z.object({
  lotId: z.string().uuid().optional(),
  range: z.enum(["last_7d", "last_30d"]).optional(),
});

export type LoginDto = z.infer<typeof LoginSchema>;
export type RefreshTokenDto = z.infer<typeof RefreshTokenSchema>;
export type ApprovalDto = z.infer<typeof ApprovalSchema>;
export type RejectDto = z.infer<typeof RejectSchema>;
export type ExportQuery = z.infer<typeof ExportQuerySchema>;

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  user: User;
}

export interface User {
  id: string;
  clientId?: string | null;
  email: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  roles: UserRole[];
}

export interface Client {
  id: string;
  name: string;
  logoUrl?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface Factory {
  id: string;
  name: string;
  city?: string | null;
  country: string;
  createdAt: string;
  updatedAt: string;
  clientId?: string;
  capabilities?: FactoryCapability[];
  certifications?: FactoryCertification[];
}

export interface FactoryCertification {
  id: string;
  factoryId: string;
  certification: FactoryCertificationType | string;
  createdAt?: string;
  updatedAt?: string;
}

export interface LotSupplier {
  id?: string;
  factoryId: string;
  sequence: number;
  stage?: string | null;
  isPrimary: boolean;
  factory?: Factory;
  roles?: LotSupplierRole[];
}

export interface SupplyChainRole {
  id: string;
  key: string;
  name: string;
  description?: string | null;
  defaultSequence: number;
  defaultCo2Kg: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface FactoryCapability {
  id: string;
  factoryId: string;
  roleId: string;
  co2OverrideKg?: number | null;
  notes?: string | null;
  createdAt?: string;
  updatedAt?: string;
  role?: SupplyChainRole;
}

export interface LotSupplierRole {
  id: string;
  roleId: string;
  sequence: number;
  co2Kg?: number | null;
  notes?: string | null;
  createdAt?: string;
  updatedAt?: string;
  role?: SupplyChainRole;
  status?: SupplyChainStageStatus;
  startedAt?: string | null;
  completedAt?: string | null;
}

export interface Lot {
  id: string;
  clientId: string;
  factoryId: string;
  primaryFactoryId?: string;
  styleRef: string;
  quantityTotal: number;
  status: LotStatus;
  defectRate: number;
  inspectedProgress: number;
  createdAt: string;
  updatedAt: string;
  factory?: Factory;
  client?: Client;
  latestInspection?: Inspection;
  approvals?: Approval[];
  inspections?: Inspection[];
  suppliers?: LotSupplier[];
}

export interface Inspection {
  id: string;
  lotId: string;
  inspectorId?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  createdAt: string;
  updatedAt: string;
  defects?: Defect[];
  lot?: Lot;
}

export interface Defect {
  id: string;
  inspectionId: string;
  pieceCode?: string | null;
  note?: string | null;
  defectTypeId?: string | null;
  createdAt: string;
  updatedAt: string;
  photos: Photo[];
}

export interface Photo {
  id: string;
  defectId: string;
  url: string;
  annotation?: PhotoAnnotation;
  createdAt: string;
  updatedAt: string;
}

export interface PhotoAnnotation {
  comment?: string;
  points?: Array<{ x: number; y: number; note?: string }>;
}

export interface DefectRateAnalytics {
  groupBy?: "style" | "factory";
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
    type: string;
    count: number;
    percentage: number;
  }>;
}

export interface ApprovalTimeAnalytics {
  average: number;
  p50: number;
  p90: number;
}

export interface Approval {
  id: string;
  lotId: string;
  approvedBy?: string | null;
  decision: ApprovalDecision;
  decidedAt: string;
  note?: string | null;
}

export interface Report {
  id: string;
  type: ReportType;
  clientId?: string | null;
  lotId?: string | null;
  month?: string | null;
  url?: string | null;
  status: ReportStatus;
  createdAt: string;
}

export interface Activity {
  id: string;
  lotId: string;
  ts: string;
  kind: string;
  payload: Record<string, unknown>;
}

export interface Event {
  id: string;
  type: EventType;
  payload: Record<string, unknown>;
  createdAt: string;
}

export interface AuditLogEntry {
  id: number;
  userId?: string | null;
  entity: string;
  entityId: string;
  action: "CREATE" | "UPDATE" | "DELETE";
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  ts: string;
}

export interface SupplierScorecardRow {
  factoryName: string;
  totalLots: number;
  approvedLots: number;
  rejectedLots: number;
  defectRateAverage: number;
}

export interface SupplierScorecardReport {
  clientId: string;
  month: string;
  rows: SupplierScorecardRow[];
  generatedAt: string;
}

export interface TrendPoint {
  date: string;
  value: number;
}

export interface DefectTrend {
  defectType: string;
  points: TrendPoint[];
}
