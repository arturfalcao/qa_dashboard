import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { InspectionSession } from "../entities/inspection-session.entity";
import { Approval } from "../entities/approval.entity";
import { PieceDefect } from "../entities/piece-defect.entity";
import {
  DefectRateAnalytics,
  ThroughputAnalytics,
  DefectTypeAnalytics,
  ApprovalTimeAnalytics,
} from "@qa-dashboard/shared";

@Injectable()
export class AnalyticsService {
  constructor(
    @InjectRepository(InspectionSession)
    private inspectionSessionRepository: Repository<InspectionSession>,
    @InjectRepository(Approval)
    private approvalRepository: Repository<Approval>,
    @InjectRepository(PieceDefect)
    private pieceDefectRepository: Repository<PieceDefect>,
  ) {}

  async getDefectRate(
    tenantId: string,
    range: "last_7d" | "last_30d" = "last_7d",
    groupBy?: "style" | "factory",
  ): Promise<DefectRateAnalytics> {
    const days = range === "last_7d" ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    if (groupBy === "factory") {
      // Group by factory using lot_factories relationship
      const results = await this.inspectionSessionRepository
        .createQueryBuilder("session")
        .innerJoin("session.lot", "lot")
        .leftJoin("lot.lotFactories", "lf")
        .leftJoin("lf.factory", "factory")
        .select([
          "COALESCE(factory.name, 'Unknown') as name",
          "SUM(session.piecesInspected) as totalInspected",
          "SUM(session.piecesDefect) as totalDefects",
        ])
        .where("lot.tenantId = :tenantId", { tenantId })
        .andWhere("session.createdAt >= :since", { since })
        .groupBy("factory.id, factory.name")
        .getRawMany();

      return {
        groupBy,
        data: results.map((row) => ({
          name: row.name || "Unknown",
          totalInspected: Number(row.totalinspected) || 0,
          totalDefects: Number(row.totaldefects) || 0,
          defectRate:
            Number(row.totalinspected) > 0
              ? (Number(row.totaldefects) / Number(row.totalinspected)) * 100
              : 0,
        })),
      };
    } else if (groupBy === "style") {
      // Group by style reference
      const results = await this.inspectionSessionRepository
        .createQueryBuilder("session")
        .innerJoin("session.lot", "lot")
        .select([
          "lot.styleRef as name",
          "SUM(session.piecesInspected) as totalInspected",
          "SUM(session.piecesDefect) as totalDefects",
        ])
        .where("lot.tenantId = :tenantId", { tenantId })
        .andWhere("session.createdAt >= :since", { since })
        .groupBy("lot.styleRef")
        .getRawMany();

      return {
        groupBy,
        data: results.map((row) => ({
          name: row.name || "Unknown",
          totalInspected: Number(row.totalinspected) || 0,
          totalDefects: Number(row.totaldefects) || 0,
          defectRate:
            Number(row.totalinspected) > 0
              ? (Number(row.totaldefects) / Number(row.totalinspected)) * 100
              : 0,
        })),
      };
    } else {
      // Overall metrics
      const result = await this.inspectionSessionRepository
        .createQueryBuilder("session")
        .innerJoin("session.lot", "lot")
        .select([
          "SUM(session.piecesInspected) as totalInspected",
          "SUM(session.piecesDefect) as totalDefects",
        ])
        .where("lot.tenantId = :tenantId", { tenantId })
        .andWhere("session.createdAt >= :since", { since })
        .getRawOne();

      const totalInspected = Number(result?.totalinspected) || 0;
      const totalDefects = Number(result?.totaldefects) || 0;

      return {
        groupBy,
        data: [
          {
            name: "Overall",
            defectRate:
              totalInspected > 0 ? (totalDefects / totalInspected) * 100 : 0,
            totalInspected,
            totalDefects,
          },
        ],
      };
    }
  }

  async getThroughput(
    tenantId: string,
    bucket: "day" | "week" = "day",
    range: "last_7d" | "last_30d" = "last_7d",
  ): Promise<ThroughputAnalytics> {
    const days = range === "last_7d" ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    const dateFormat = bucket === "day" ? "YYYY-MM-DD" : 'IYYY-"W"IW';

    const query = this.inspectionSessionRepository
      .createQueryBuilder("session")
      .select([
        `TO_CHAR(session.createdAt, '${dateFormat}') as date`,
        "COUNT(*) as inspections",
        "SUM(session.piecesInspected) as piecesInspected",
      ])
      .innerJoin("session.lot", "lot")
      .where("lot.tenantId = :tenantId", { tenantId })
      .andWhere("session.createdAt >= :since", { since })
      .groupBy(`TO_CHAR(session.createdAt, '${dateFormat}')`)
      .orderBy("date", "ASC");

    const results = await query.getRawMany();

    return {
      data: results.map((row) => ({
        date: row.date,
        inspections: Number(row.inspections) || 0,
        piecesInspected: Number(row.piecesinspected) || 0,
      })),
    };
  }

  async getDefectTypes(
    tenantId: string,
    range: "last_7d" | "last_30d" = "last_7d",
  ): Promise<DefectTypeAnalytics> {
    const days = range === "last_7d" ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    // Extract defect types from audio transcripts
    // Since piece_defects don't have defect_type_id, we'll categorize by status
    const results = await this.pieceDefectRepository
      .createQueryBuilder("defect")
      .innerJoin("defect.piece", "piece")
      .innerJoin("piece.session", "session")
      .innerJoin("session.lot", "lot")
      .select([
        "defect.status as type",
        "COUNT(defect.id) as count",
      ])
      .where("lot.tenantId = :tenantId", { tenantId })
      .andWhere("defect.createdAt >= :since", { since })
      .groupBy("defect.status")
      .getRawMany();

    const totalDefects = results.reduce(
      (sum, row) => sum + Number(row.count || 0),
      0,
    );

    return {
      data: results.map((row) => ({
        type: row.type === "confirmed" ? "Confirmed Defects" : row.type === "pending_review" ? "Pending Review" : "Rejected",
        count: Number(row.count) || 0,
        percentage:
          totalDefects > 0 ? (Number(row.count || 0) / totalDefects) * 100 : 0,
      })),
    };
  }

  async getApprovalTime(
    tenantId: string,
    range: "last_7d" | "last_30d" = "last_7d",
  ): Promise<ApprovalTimeAnalytics> {
    const days = range === "last_7d" ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    const results = await this.approvalRepository
      .createQueryBuilder("approval")
      .innerJoin("approval.lot", "lot")
      .select([
        "EXTRACT(EPOCH FROM (approval.decidedAt - lot.createdAt)) / 3600 as approvalTimeHours",
      ])
      .where("lot.tenantId = :tenantId", { tenantId })
      .andWhere("approval.decidedAt >= :since", { since })
      .getRawMany();

    const approvalTimes = results
      .map((r) => Number(r.approvaltimehours))
      .filter((t) => Number.isFinite(t) && t >= 0)
      .sort((a, b) => a - b);

    if (approvalTimes.length === 0) {
      return { average: 0, p50: 0, p90: 0 };
    }

    const average =
      approvalTimes.reduce((sum, time) => sum + time, 0) / approvalTimes.length;
    const p50Index = Math.max(0, Math.floor(approvalTimes.length * 0.5) - 1);
    const p90Index = Math.max(0, Math.floor(approvalTimes.length * 0.9) - 1);

    return {
      average: Math.round(average * 100) / 100,
      p50: Math.round(approvalTimes[p50Index] * 100) / 100,
      p90: Math.round(approvalTimes[p90Index] * 100) / 100,
    };
  }
}
