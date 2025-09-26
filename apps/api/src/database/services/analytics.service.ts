import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { Inspection } from "../entities/inspection.entity";
import { Approval } from "../entities/approval.entity";
import { Defect } from "../entities/defect.entity";
import {
  DefectRateAnalytics,
  ThroughputAnalytics,
  DefectTypeAnalytics,
  ApprovalTimeAnalytics,
} from "@qa-dashboard/shared";

@Injectable()
export class AnalyticsService {
  constructor(
    @InjectRepository(Inspection)
    private inspectionRepository: Repository<Inspection>,
    @InjectRepository(Approval)
    private approvalRepository: Repository<Approval>,
    @InjectRepository(Defect)
    private defectRepository: Repository<Defect>,
  ) {}

  async getDefectRate(
    clientId: string,
    range: "last_7d" | "last_30d" = "last_7d",
    groupBy?: "style" | "factory",
  ): Promise<DefectRateAnalytics> {
    const days = range === "last_7d" ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    let query = this.inspectionRepository
      .createQueryBuilder("ins")
      .innerJoin("ins.lot", "lot")
      .where("lot.clientId = :clientId", { clientId })
      .andWhere("ins.createdAt >= :since", { since });

    if (groupBy === "factory") {
      query = query
        .leftJoin("lot.factory", "factory")
        .select([
          "factory.name as name",
          "COUNT(*) as totalInspected",
          "SUM(CASE WHEN defects.count > 0 THEN 1 ELSE 0 END) as totalDefects",
        ])
        .leftJoin(
          (qb) =>
            qb
              .select("defect.inspection_id", "inspectionId")
              .addSelect("COUNT(defect.id)", "count")
              .from(Defect, "defect")
              .groupBy("defect.inspection_id"),
          "defects",
          "defects.\"inspectionId\" = ins.id",
        )
        .groupBy("factory.id, factory.name");
    } else if (groupBy === "style") {
      query = query
        .select([
          "lot.styleRef as name",
          "COUNT(*) as totalInspected",
          "SUM(CASE WHEN defects.count > 0 THEN 1 ELSE 0 END) as totalDefects",
        ])
        .leftJoin(
          (qb) =>
            qb
              .select("defect.inspection_id", "inspectionId")
              .addSelect("COUNT(defect.id)", "count")
              .from(Defect, "defect")
              .groupBy("defect.inspection_id"),
          "defects",
          "defects.\"inspectionId\" = ins.id",
        )
        .groupBy("lot.styleRef");
    } else {
      const totalInspected = await this.inspectionRepository
        .createQueryBuilder("ins")
        .innerJoin("ins.lot", "lot")
        .where("lot.clientId = :clientId", { clientId })
        .andWhere("ins.createdAt >= :since", { since })
        .getCount();

      const totalDefects = await this.defectRepository
        .createQueryBuilder("defect")
        .innerJoin("defect.inspection", "inspection")
        .innerJoin("inspection.lot", "lot")
        .where("lot.clientId = :clientId", { clientId })
        .andWhere("inspection.createdAt >= :since", { since })
        .getCount();

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

    const results = await query.getRawMany();

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
  }

  async getThroughput(
    clientId: string,
    bucket: "day" | "week" = "day",
    range: "last_7d" | "last_30d" = "last_7d",
  ): Promise<ThroughputAnalytics> {
    const days = range === "last_7d" ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    const dateFormat = bucket === "day" ? "YYYY-MM-DD" : 'IYYY-"W"IW';

    const query = this.inspectionRepository
      .createQueryBuilder("ins")
      .select([
        `TO_CHAR(ins.createdAt, '${dateFormat}') as date`,
        "COUNT(*) as inspections",
      ])
      .innerJoin("ins.lot", "lot")
      .where("lot.clientId = :clientId", { clientId })
      .andWhere("ins.createdAt >= :since", { since })
      .groupBy(`TO_CHAR(ins.createdAt, '${dateFormat}')`)
      .orderBy("date", "ASC");

    const results = await query.getRawMany();

    return {
      data: results.map((row) => ({
        date: row.date,
        inspections: Number(row.inspections) || 0,
      })),
    };
  }

  async getDefectTypes(
    clientId: string,
    range: "last_7d" | "last_30d" = "last_7d",
  ): Promise<DefectTypeAnalytics> {
    const days = range === "last_7d" ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    const results = await this.defectRepository
      .createQueryBuilder("defect")
      .leftJoin("defect.defectType", "type")
      .innerJoin("defect.inspection", "inspection")
      .innerJoin("inspection.lot", "lot")
      .select([
        "COALESCE(type.name, 'Unclassified') as type",
        "COUNT(defect.id) as count",
      ])
      .where("lot.clientId = :clientId", { clientId })
      .andWhere("defect.createdAt >= :since", { since })
      .groupBy("type.name")
      .getRawMany();

    const totalDefects = results.reduce(
      (sum, row) => sum + Number(row.count || 0),
      0,
    );

    return {
      data: results.map((row) => ({
        type: row.type,
        count: Number(row.count) || 0,
        percentage:
          totalDefects > 0 ? (Number(row.count || 0) / totalDefects) * 100 : 0,
      })),
    };
  }

  async getApprovalTime(
    clientId: string,
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
      .where("lot.clientId = :clientId", { clientId })
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
