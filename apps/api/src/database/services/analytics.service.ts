import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Inspection } from '../entities/inspection.entity';
import { Approval } from '../entities/approval.entity';
import { DefectType, DefectRateAnalytics, ThroughputAnalytics, DefectTypeAnalytics, ApprovalTimeAnalytics } from '@qa-dashboard/shared';

@Injectable()
export class AnalyticsService {
  constructor(
    @InjectRepository(Inspection)
    private inspectionRepository: Repository<Inspection>,
    @InjectRepository(Approval)
    private approvalRepository: Repository<Approval>,
  ) {}

  async getDefectRate(
    tenantId: string,
    range: 'last_7d' | 'last_30d' = 'last_7d',
    groupBy?: 'style' | 'vendor',
  ): Promise<DefectRateAnalytics> {
    const days = range === 'last_7d' ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    let query = this.inspectionRepository
      .createQueryBuilder('i')
      .leftJoin('i.garment', 'g')
      .leftJoin('g.batch', 'b')
      .leftJoin('b.vendor', 'v')
      .leftJoin('b.style', 's')
      .where('i.tenantId = :tenantId', { tenantId })
      .andWhere('i.inspectedAt >= :since', { since });

    if (groupBy === 'vendor') {
      query = query
        .select([
          'v.name as name',
          'COUNT(*) as totalInspected',
          'COUNT(CASE WHEN i.hasDefect = true THEN 1 END) as totalDefects',
        ])
        .groupBy('v.id, v.name');
    } else if (groupBy === 'style') {
      query = query
        .select([
          's.styleCode as name',
          'COUNT(*) as totalInspected',
          'COUNT(CASE WHEN i.hasDefect = true THEN 1 END) as totalDefects',
        ])
        .groupBy('s.id, s.styleCode');
    } else {
      const totalInspected = await this.inspectionRepository
        .createQueryBuilder('i')
        .where('i.tenantId = :tenantId', { tenantId })
        .andWhere('i.inspectedAt >= :since', { since })
        .getCount();

      const totalDefects = await this.inspectionRepository
        .createQueryBuilder('i')
        .where('i.tenantId = :tenantId', { tenantId })
        .andWhere('i.hasDefect = true')
        .andWhere('i.inspectedAt >= :since', { since })
        .getCount();

      return {
        groupBy,
        data: [
          {
            name: 'Overall',
            defectRate: totalInspected > 0 ? (totalDefects / totalInspected) * 100 : 0,
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
        name: row.name,
        totalInspected: parseInt(row.totalinspected),
        totalDefects: parseInt(row.totaldefects),
        defectRate:
          row.totalinspected > 0
            ? (parseInt(row.totaldefects) / parseInt(row.totalinspected)) * 100
            : 0,
      })),
    };
  }

  async getThroughput(
    tenantId: string,
    bucket: 'day' | 'week' = 'day',
    range: 'last_7d' | 'last_30d' = 'last_7d',
  ): Promise<ThroughputAnalytics> {
    const days = range === 'last_7d' ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    const dateFormat = bucket === 'day' ? 'YYYY-MM-DD' : 'YYYY-"W"WW';
    
    const query = this.inspectionRepository
      .createQueryBuilder('i')
      .select([
        `TO_CHAR(i.inspectedAt, '${dateFormat}') as date`,
        'COUNT(*) as inspections',
      ])
      .where('i.tenantId = :tenantId', { tenantId })
      .andWhere('i.inspectedAt >= :since', { since })
      .groupBy(`TO_CHAR(i.inspectedAt, '${dateFormat}')`)
      .orderBy('date', 'ASC');

    const results = await query.getRawMany();

    return {
      data: results.map((row) => ({
        date: row.date,
        inspections: parseInt(row.inspections),
      })),
    };
  }

  async getDefectTypes(
    tenantId: string,
    range: 'last_7d' | 'last_30d' = 'last_7d',
  ): Promise<DefectTypeAnalytics> {
    const days = range === 'last_7d' ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    const results = await this.inspectionRepository
      .createQueryBuilder('i')
      .select([
        'i.defectType as type',
        'COUNT(*) as count',
      ])
      .where('i.tenantId = :tenantId', { tenantId })
      .andWhere('i.hasDefect = true')
      .andWhere('i.inspectedAt >= :since', { since })
      .groupBy('i.defectType')
      .getRawMany();

    const totalDefects = results.reduce((sum, row) => sum + parseInt(row.count), 0);

    return {
      data: results.map((row) => ({
        type: row.type as DefectType,
        count: parseInt(row.count),
        percentage: totalDefects > 0 ? (parseInt(row.count) / totalDefects) * 100 : 0,
      })),
    };
  }

  async getApprovalTime(
    tenantId: string,
    range: 'last_7d' | 'last_30d' = 'last_7d',
  ): Promise<ApprovalTimeAnalytics> {
    const days = range === 'last_7d' ? 7 : 30;
    const since = new Date();
    since.setDate(since.getDate() - days);

    // Get approval times (in hours)
    const results = await this.approvalRepository
      .createQueryBuilder('a')
      .leftJoin('a.batch', 'b')
      .select([
        'EXTRACT(EPOCH FROM (a.decidedAt - b.updatedAt)) / 3600 as approvalTimeHours',
      ])
      .where('a.tenantId = :tenantId', { tenantId })
      .andWhere('a.decidedAt >= :since', { since })
      .getRawMany();

    const approvalTimes = results.map((r) => parseFloat(r.approvaltimehours)).filter(t => t > 0);

    if (approvalTimes.length === 0) {
      return { average: 0, p50: 0, p90: 0 };
    }

    approvalTimes.sort((a, b) => a - b);
    
    const average = approvalTimes.reduce((sum, time) => sum + time, 0) / approvalTimes.length;
    const p50Index = Math.floor(approvalTimes.length * 0.5);
    const p90Index = Math.floor(approvalTimes.length * 0.9);

    return {
      average: Math.round(average * 100) / 100,
      p50: Math.round(approvalTimes[p50Index] * 100) / 100,
      p90: Math.round(approvalTimes[p90Index] * 100) / 100,
    };
  }
}