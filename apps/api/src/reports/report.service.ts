import { Injectable, NotFoundException, BadRequestException, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import * as crypto from 'crypto';
import { Report } from '../database/entities/report.entity';
import { ReportType, ReportStatus, ReportLanguage } from '@qa-dashboard/shared';
import {
  ReportGenerationRequest,
  ReportGenerationResult,
  ExecutiveQualitySummaryData,
  LotInspectionReportData,
  MeasurementComplianceSheetData,
  PackagingReadinessReportData,
  DppSummaryReportData,
  ExecutiveQualitySummaryParams,
  LotInspectionReportParams,
  MeasurementComplianceSheetParams,
  PackagingReadinessReportParams,
  DppSummaryParams,
} from './report-types';
import { AnalyticsService } from '../database/services/analytics.service';
import { ClientService } from '../database/services/client.service';
import { LotService } from '../database/services/lot.service';
import { InspectionService } from '../database/services/inspection.service';
import { StorageService } from '../storage/storage.service';
import { launchPuppeteer } from '../common/puppeteer';

@Injectable()
export class ReportService {
  private readonly logger = new Logger(ReportService.name);

  constructor(
    @InjectRepository(Report)
    private reportRepository: Repository<Report>,
    private analyticsService: AnalyticsService,
    private clientService: ClientService,
    private lotService: LotService,
    private inspectionService: InspectionService,
    private storageService: StorageService,
  ) {}

  async generateReport(request: ReportGenerationRequest): Promise<ReportGenerationResult> {
    const startTime = Date.now();

    try {
      this.logger.log(`Starting report generation: ${request.type} for client ${request.clientId}`);

      // Create report record
      const fileName = this.generateFileName(request.type, request.clientId);
      const report = this.reportRepository.create({
        clientId: request.clientId,
        userId: request.userId,
        type: request.type,
        language: request.language || ReportLanguage.EN,
        status: ReportStatus.GENERATING,
        fileName,
        parameters: request.parameters,
        metadata: request.metadata,
      });

      const savedReport = await this.reportRepository.save(report);

      try {
        // Generate the report based on type
        const minioKey = await this.generateReportByType(savedReport);

        // Update report with success
        savedReport.status = ReportStatus.COMPLETED;
        savedReport.filePath = minioKey;
        savedReport.fileUrl = `/api/reports/${savedReport.id}/download`;
        savedReport.fileSize = 0; // File size not tracked for MinIO uploads
        savedReport.generatedAt = new Date();
        savedReport.expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days
        savedReport.generationTimeMs = Date.now() - startTime;

        await this.reportRepository.save(savedReport);

        this.logger.log(`Report generated successfully: ${savedReport.id} (${savedReport.generationTimeMs}ms)`);

        return {
          id: savedReport.id,
          type: savedReport.type,
          status: savedReport.status,
          fileName: savedReport.fileName,
          url: savedReport.fileUrl,
          filePath: savedReport.filePath,
          size: savedReport.fileSize,
          generatedAt: savedReport.generatedAt,
          expiresAt: savedReport.expiresAt,
          metadata: savedReport.metadata,
        };

      } catch (generationError) {
        this.logger.error(`Report generation failed: ${generationError.message}`, generationError.stack);

        // Update report with error
        savedReport.status = ReportStatus.FAILED;
        savedReport.errorMessage = generationError.message;
        savedReport.generationTimeMs = Date.now() - startTime;
        await this.reportRepository.save(savedReport);

        throw generationError;
      }

    } catch (error) {
      this.logger.error(`Failed to generate report: ${error.message}`, error.stack);
      throw new BadRequestException(`Report generation failed: ${error.message}`);
    }
  }

  private async generateReportByType(report: Report): Promise<string> {
    switch (report.type) {
      case ReportType.EXECUTIVE_QUALITY_SUMMARY:
        return await this.generateExecutiveQualitySummary(report);
      case ReportType.LOT_INSPECTION_REPORT:
        return await this.generateLotInspectionReport(report);
      case ReportType.MEASUREMENT_COMPLIANCE_SHEET:
        return await this.generateMeasurementComplianceSheet(report);
      case ReportType.PACKAGING_READINESS_REPORT:
        return await this.generatePackagingReadinessReport(report);
      case ReportType.DPP_SUMMARY:
        return await this.generateDppSummaryReport(report);
      // Add other report types here
      default:
        throw new BadRequestException(`Unsupported report type: ${report.type}`);
    }
  }

  private async generateExecutiveQualitySummary(report: Report): Promise<string> {
    const params = report.parameters as ExecutiveQualitySummaryParams;

    // Get data for the report
    const data: ExecutiveQualitySummaryData = await this.getExecutiveQualitySummaryData(
      report.clientId,
      params
    );

    // Generate HTML content
    const htmlContent = this.renderExecutiveQualitySummaryTemplate(data, report.language);

    // Convert to PDF
    const key = await this.generatePDF(htmlContent, report.fileName, report.clientId, {
      format: 'A4',
      margin: { top: '20px', right: '20px', bottom: '20px', left: '20px' },
      displayHeaderFooter: true,
      headerTemplate: this.getHeaderTemplate(data.client, report.language),
      footerTemplate: this.getFooterTemplate(report.language),
    });

    return key;
  }

  private async generateLotInspectionReport(report: Report): Promise<string> {
    const params = report.parameters as LotInspectionReportParams;

    // Get data for the report
    const data: LotInspectionReportData = await this.getLotInspectionReportData(
      report.clientId,
      params
    );

    // Generate HTML content
    const htmlContent = this.renderLotInspectionReportTemplate(data, report.language);

    // Convert to PDF
    const key = await this.generatePDF(htmlContent, report.fileName, report.clientId, {
      format: 'A4',
      margin: { top: '60px', right: '20px', bottom: '60px', left: '20px' },
      displayHeaderFooter: true,
      headerTemplate: this.getHeaderTemplate(data.lot, report.language),
      footerTemplate: this.getFooterTemplate(report.language),
    });

    return key;
  }

  private async generateMeasurementComplianceSheet(report: Report): Promise<string> {
    const params = report.parameters as MeasurementComplianceSheetParams;

    // Get data for the report
    const data: MeasurementComplianceSheetData = await this.getMeasurementComplianceSheetData(
      report.clientId,
      params
    );

    // Generate HTML content
    const htmlContent = this.renderMeasurementComplianceSheetTemplate(data, report.language);

    // Convert to PDF
    const key = await this.generatePDF(htmlContent, report.fileName, report.clientId, {
      format: 'A4',
      margin: { top: '60px', right: '20px', bottom: '60px', left: '20px' },
      displayHeaderFooter: true,
      headerTemplate: this.getHeaderTemplate(data.lot, report.language),
      footerTemplate: this.getFooterTemplate(report.language),
    });

    return key;
  }

  private async generatePackagingReadinessReport(report: Report): Promise<string> {
    const params = report.parameters as PackagingReadinessReportParams;

    // Get packaging readiness data
    const data: PackagingReadinessReportData = await this.getPackagingReadinessReportData(
      report.clientId,
      params
    );

    // Generate HTML content
    const htmlContent = this.renderPackagingReadinessReportTemplate(data, report.language);

    // Generate PDF
    const fileName = this.generateFileName(report.type, report.clientId);
    const key = await this.generatePDF(htmlContent, fileName, report.clientId, {
      format: 'A4',
      printBackground: true,
      margin: { top: '20px', right: '20px', bottom: '20px', left: '20px' }
    });

    return key;
  }

  private async generatePDF(htmlContent: string, fileName: string, clientId: string, options: any): Promise<string> {
    const browser = await launchPuppeteer({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
      const page = await browser.newPage();
      await page.setContent(htmlContent, { waitUntil: 'networkidle2' });

      const pdfBuffer = await page.pdf({
        ...options,
      });

      // Upload to MinIO and return the key
      const key = await this.storageService.uploadFile(
        Buffer.from(pdfBuffer),
        fileName,
        'application/pdf',
        clientId,
        'reports'
      );

      return key;
    } finally {
      await browser.close();
    }
  }

  private generateFileName(reportType: ReportType, clientId: string): string {
    const timestamp = new Date().toISOString().split('T')[0];
    const hash = crypto.randomBytes(4).toString('hex');
    return `${reportType.toLowerCase()}_${clientId.slice(0, 8)}_${timestamp}_${hash}.pdf`;
  }


  private getHeaderTemplate(clientData: any, language: ReportLanguage): string {
    return `
      <div style="font-size: 10px; padding: 5px; width: 100%; display: flex; justify-content: space-between;">
        <div style="flex: 1;">
          ${clientData.name || clientData.factory?.name || 'QA Dashboard'}
        </div>
        <div style="flex: 1; text-align: right;">
          <span class="pageNumber"></span> / <span class="totalPages"></span>
        </div>
      </div>
    `;
  }

  private getFooterTemplate(language: ReportLanguage): string {
    const footerText = language === ReportLanguage.PT ?
      'Gerado por Pack & Polish QA Dashboard' :
      language === ReportLanguage.ES ?
      'Generado por Pack & Polish QA Dashboard' :
      'Generated by Pack & Polish QA Dashboard';

    return `
      <div style="font-size: 8px; padding: 5px; width: 100%; text-align: center; color: #666;">
        ${footerText}
      </div>
    `;
  }

  private async getExecutiveQualitySummaryData(
    clientId: string,
    params: ExecutiveQualitySummaryParams
  ): Promise<ExecutiveQualitySummaryData> {
    const { period } = params;

    // Calculate the date range for analytics
    const days = Math.ceil((new Date(period.endDate).getTime() - new Date(period.startDate).getTime()) / (1000 * 60 * 60 * 24));
    const range = days <= 7 ? 'last_7d' : 'last_30d';

    // Fetch client information
    const client = await this.clientService.findById(clientId);

    // Fetch analytics data in parallel
    const [
      defectRateData,
      defectTypeData,
      approvalTimeData,
      supplierPerformanceData,
      throughputData,
      lots
    ] = await Promise.all([
      this.analyticsService.getDefectRate(clientId, range),
      this.analyticsService.getDefectTypes(clientId, range),
      this.analyticsService.getApprovalTime(clientId, range),
      this.analyticsService.getDefectRate(clientId, range, 'factory'),
      this.analyticsService.getThroughput(clientId, 'day', range),
      this.lotService.listLots(clientId)
    ]);

    // Calculate KPIs
    const overallDefectRate = defectRateData.data[0]?.defectRate || 0;
    const firstPassYield = 100 - overallDefectRate;
    const averageLeadTime = approvalTimeData.average / 24; // Convert hours to days

    // Get top defects
    const topDefects = defectTypeData.data
      .sort((a, b) => b.count - a.count)
      .slice(0, 5)
      .map(defect => ({
        name: defect.type,
        count: defect.count,
        percentage: defect.percentage
      }));

    // Get supplier performance (top 5 by volume)
    const supplierPerformance = supplierPerformanceData.data
      .sort((a, b) => b.totalInspected - a.totalInspected)
      .slice(0, 5)
      .map(supplier => ({
        name: supplier.name,
        defectRate: supplier.defectRate,
        performance: supplier.defectRate < 2 ? 'good' as const :
                    supplier.defectRate < 5 ? 'average' as const :
                    'poor' as const
      }));

    // Generate insights
    const insights = this.generateExecutiveInsights({
      defectRate: overallDefectRate,
      firstPassYield,
      averageLeadTime,
      topDefects,
      supplierPerformance,
      throughputTrend: throughputData.data
    });

    // Calculate coverage stats
    const uniqueStyles = new Set(lots.map((lot: any) => lot.styleRef)).size;
    const totalQuantity = lots.reduce((sum: number, lot: any) => sum + (lot.quantityTotal || 0), 0);

    return {
      client: {
        name: client.name,
        logo: client.logoUrl
      },
      period: params.period,
      kpis: {
        averageDefectRate: Math.round(overallDefectRate * 10) / 10,
        firstPassYield: Math.round(firstPassYield * 10) / 10,
        averageLeadTime: Math.round(averageLeadTime * 10) / 10
      },
      topDefects,
      supplierPerformance,
      insights,
      coverageStats: {
        purchaseOrders: lots.length,
        styles: uniqueStyles,
        totalQuantity
      }
    };
  }

  private generateExecutiveInsights(data: {
    defectRate: number;
    firstPassYield: number;
    averageLeadTime: number;
    topDefects: Array<{ name: string; count: number; percentage: number }>;
    supplierPerformance: Array<{ name: string; defectRate: number; performance: string }>;
    throughputTrend: Array<{ date: string; inspections: number }>;
  }): string[] {
    const insights = [];

    // Quality insights
    if (data.defectRate < 2) {
      insights.push('📈 Quality performance is excellent with defect rate below 2%');
    } else if (data.defectRate > 5) {
      insights.push('🚨 Quality requires immediate attention with defect rate above 5%');
    }

    // Lead time insights
    if (data.averageLeadTime < 2) {
      insights.push('⚡ Fast approval times supporting quick time-to-market');
    } else if (data.averageLeadTime > 5) {
      insights.push('⏳ Approval bottlenecks may be impacting delivery schedules');
    }

    // Top defects insights
    if (data.topDefects.length > 0) {
      const topDefect = data.topDefects[0];
      insights.push(`🎯 Focus area: ${topDefect.name} represents ${Math.round(topDefect.percentage)}% of all defects`);
    }

    // Supplier insights
    const goodSuppliers = data.supplierPerformance.filter(s => s.performance === 'good').length;
    const totalSuppliers = data.supplierPerformance.length;
    if (totalSuppliers > 0) {
      const goodPercentage = Math.round((goodSuppliers / totalSuppliers) * 100);
      if (goodPercentage > 70) {
        insights.push(`✨ Strong supplier base: ${goodPercentage}% of key suppliers performing well`);
      } else {
        insights.push(`⚠️ Supplier development needed: Only ${goodPercentage}% of suppliers meeting quality targets`);
      }
    }

    return insights.slice(0, 4); // Keep it concise for executive summary
  }

  private async getLotInspectionReportData(
    clientId: string,
    params: LotInspectionReportParams
  ): Promise<LotInspectionReportData> {
    // Fetch lot data with all related information
    const lot = await this.lotService.getLot(clientId, params.lotId);
    if (!lot) {
      throw new NotFoundException(`Lot not found: ${params.lotId}`);
    }

    // Get the latest inspection for this lot
    const latestInspection = lot.latestInspection;
    if (!latestInspection) {
      throw new NotFoundException(`No inspection found for lot: ${params.lotId}`);
    }

    // Extract defects and photos from the inspection
    const defects = latestInspection.defects || [];
    const allPhotos: Array<{ url: string; caption: string; annotations?: any[] }> = [];

    // Process defects to get photos and organize defect data
    const processedDefects = defects.map(defect => {
      const defectPhotos = defect.photos || [];

      // Add defect photos to the overall photos collection
      defectPhotos.forEach(photo => {
        allPhotos.push({
          url: photo.url,
          caption: defect.note || 'Defect photo',
          annotations: photo.annotation?.points || []
        });
      });

      return {
        type: defect.defectTypeId || 'Unknown',
        count: 1,
        severity: 'major' as const, // You might want to add severity to the defect entity
        images: defectPhotos.map(photo => photo.url)
      };
    });

    // Group defects by type and count them
    const defectCounts = processedDefects.reduce((acc, defect) => {
      if (acc[defect.type]) {
        acc[defect.type].count += 1;
      } else {
        acc[defect.type] = {
          type: defect.type,
          count: 1,
          severity: defect.severity,
          images: defect.images
        };
      }
      return acc;
    }, {} as Record<string, { type: string; count: number; severity: 'critical' | 'major' | 'minor'; images?: string[]; }>);

    const finalDefects = Object.values(defectCounts) as Array<{
      type: string;
      count: number;
      severity: 'critical' | 'major' | 'minor';
      images?: string[];
    }>;

    // Get approval decision
    const approvals = lot.approvals || [];
    const latestApproval = approvals[0]; // Assuming approvals are ordered by date
    const decision = latestApproval?.decision === 'APPROVE' ? 'approved' as const :
                    latestApproval?.decision === 'REJECT' ? 'rejected' as const :
                    'correction_required' as const;

    // Extract inspector information (you might need to add inspector field to inspection entity)
    const inspectorName = 'Quality Inspector'; // Default since inspector field might not exist

    return {
      lot: {
        id: lot.id,
        styleRef: lot.styleRef,
        quantity: lot.quantityTotal,
        factory: {
          name: lot.factory?.name || 'Unknown Factory',
          location: `${lot.factory?.city || ''}, ${lot.factory?.country || ''}`.trim().replace(/^,\s*/, '') || 'Unknown Location'
        }
      },
      inspection: {
        date: latestInspection.startedAt || latestInspection.createdAt,
        inspector: inspectorName,
        duration: latestInspection.finishedAt && latestInspection.startedAt ?
          Math.round((new Date(latestInspection.finishedAt).getTime() - new Date(latestInspection.startedAt).getTime()) / (1000 * 60)) :
          0, // Duration in minutes
        status: lot.status.toLowerCase()
      },
      defects: finalDefects,
      measurements: [], // TODO: Add measurements when measurement entity is available
      photos: allPhotos,
      decision,
      comments: latestApproval?.note
    };
  }

  private async getMeasurementComplianceSheetData(
    clientId: string,
    params: MeasurementComplianceSheetParams
  ): Promise<MeasurementComplianceSheetData> {
    // Fetch lot data with all related information
    const lot = await this.lotService.getLot(clientId, params.lotId);
    if (!lot) {
      throw new NotFoundException(`Lot not found: ${params.lotId}`);
    }

    // Get the latest inspection for this lot
    const latestInspection = lot.latestInspection;
    if (!latestInspection) {
      throw new NotFoundException(`No inspection found for lot: ${params.lotId}`);
    }

    // Generate sample measurement data (in a real implementation, this would come from a measurements table)
    const sampleMeasurements = [
      {
        measurementPoint: 'Chest Width',
        specification: { target: '58', tolerance: '±1', unit: 'cm' },
        measured: { value: '57.8', unit: 'cm' },
        deviation: -0.3,
        status: 'pass' as const,
        notes: 'Within tolerance'
      },
      {
        measurementPoint: 'Shoulder to Shoulder',
        specification: { target: '45', tolerance: '±0.5', unit: 'cm' },
        measured: { value: '45.7', unit: 'cm' },
        deviation: 1.6,
        status: 'fail' as const,
        notes: 'Exceeds tolerance'
      },
      {
        measurementPoint: 'Total Length',
        specification: { target: '72', tolerance: '±1.5', unit: 'cm' },
        measured: { value: '71.5', unit: 'cm' },
        deviation: -0.7,
        status: 'pass' as const,
      },
      {
        measurementPoint: 'Sleeve Length',
        specification: { target: '24', tolerance: '±0.8', unit: 'cm' },
        measured: { value: '24.2', unit: 'cm' },
        deviation: 0.8,
        status: 'pass' as const,
      },
      {
        measurementPoint: 'Collar Width',
        specification: { target: '18', tolerance: '±0.5', unit: 'cm' },
        measured: { value: '18.9', unit: 'cm' },
        deviation: 5.0,
        status: 'fail' as const,
        notes: 'Significant deviation'
      }
    ];

    // Filter measurements by sample IDs if specified
    const measurements = params.sampleIds && params.sampleIds.length > 0
      ? sampleMeasurements.filter((_, index) => params.sampleIds!.includes(`sample-${index + 1}`))
      : sampleMeasurements;

    // Calculate summary statistics
    const totalMeasurements = measurements.length;
    const passedMeasurements = measurements.filter(m => m.status === 'pass').length;
    const failedMeasurements = totalMeasurements - passedMeasurements;
    const overallCompliance = totalMeasurements > 0 ? (passedMeasurements / totalMeasurements) * 100 : 0;

    // Determine approval status based on compliance
    const approvalStatus = overallCompliance >= 90 ? 'approved' as const :
                          overallCompliance >= 70 ? 'conditional' as const :
                          'rejected' as const;

    // Get approval decision
    const approvals = lot.approvals || [];
    const latestApproval = approvals[0];

    return {
      lot: {
        id: lot.id,
        styleRef: lot.styleRef,
        quantity: lot.quantityTotal,
        factory: {
          name: lot.factory?.name || 'Unknown Factory',
          location: `${lot.factory?.city || ''}, ${lot.factory?.country || ''}`.trim().replace(/^,\s*/, '') || 'Unknown Location'
        }
      },
      inspection: {
        date: latestInspection.startedAt || latestInspection.createdAt,
        inspector: 'Quality Inspector', // Default since inspector field might not exist
        status: lot.status.toLowerCase()
      },
      measurements,
      summary: {
        totalMeasurements,
        passedMeasurements,
        failedMeasurements,
        overallCompliance: Math.round(overallCompliance * 100) / 100
      },
      approvalStatus,
      comments: latestApproval?.note
    };
  }

  private async getPackagingReadinessReportData(
    clientId: string,
    params: PackagingReadinessReportParams
  ): Promise<PackagingReadinessReportData> {
    // Fetch lot data with all related information
    const lot = await this.lotService.getLot(clientId, params.lotId);
    if (!lot) {
      throw new NotFoundException(`Lot not found: ${params.lotId}`);
    }

    // Get the latest inspection for this lot
    const latestInspection = lot.latestInspection;
    if (!latestInspection) {
      throw new NotFoundException(`No inspection found for lot: ${params.lotId}`);
    }

    // Get approval decision
    const approvals = lot.approvals || [];
    const latestApproval = approvals[0]; // Assuming approvals are ordered by date
    const finalApproval = latestApproval?.decision === 'APPROVE' ? 'approved' as const :
      latestApproval?.decision === 'REJECT' ? 'rejected' as const : 'conditional' as const;

    // Sample packaging checklist data
    const sampleChecklist = [
      {
        category: 'Garment Preparation',
        items: [
          { name: 'Final pressing/steaming completed', status: 'completed' as const, checkedBy: 'Quality Team', checkedAt: '2024-01-15T10:30:00Z' },
          { name: 'Size labels attached correctly', status: 'completed' as const, checkedBy: 'Quality Team', checkedAt: '2024-01-15T10:45:00Z' },
          { name: 'Care labels attached correctly', status: 'completed' as const, checkedBy: 'Quality Team', checkedAt: '2024-01-15T10:50:00Z' },
          { name: 'Brand labels/tags attached', status: 'pending' as const },
        ]
      },
      {
        category: 'Packaging Materials',
        items: [
          { name: 'Poly bags quality check', status: 'completed' as const, checkedBy: 'Packaging Team', checkedAt: '2024-01-15T11:00:00Z' },
          { name: 'Hangers/clips prepared', status: 'completed' as const, checkedBy: 'Packaging Team', checkedAt: '2024-01-15T11:15:00Z' },
          { name: 'Carton boxes inspected', status: 'completed' as const, checkedBy: 'Packaging Team', checkedAt: '2024-01-15T11:30:00Z' },
        ]
      },
      {
        category: 'Documentation',
        items: [
          { name: 'Packing list prepared', status: 'completed' as const, checkedBy: 'Logistics', checkedAt: '2024-01-15T12:00:00Z' },
          { name: 'Shipping labels generated', status: 'completed' as const, checkedBy: 'Logistics', checkedAt: '2024-01-15T12:15:00Z' },
          { name: 'Certificate of compliance attached', status: 'pending' as const },
        ]
      }
    ];

    const totalItems = sampleChecklist.reduce((sum, category) => sum + category.items.length, 0);
    const completedItems = sampleChecklist.reduce((sum, category) =>
      sum + category.items.filter(item => item.status === 'completed').length, 0
    );
    const completionPercentage = Math.round((completedItems / totalItems) * 100);

    // Sample packaging photos
    const samplePhotos = [
      { url: '/packaging/photo1.jpg', caption: 'Final garment inspection', category: 'quality_control' as const, takenAt: '2024-01-15T14:00:00Z' },
      { url: '/packaging/photo2.jpg', caption: 'Packaging materials setup', category: 'packaging' as const, takenAt: '2024-01-15T14:15:00Z' },
      { url: '/packaging/photo3.jpg', caption: 'Label attachment verification', category: 'labeling' as const, takenAt: '2024-01-15T14:30:00Z' },
      { url: '/packaging/photo4.jpg', caption: 'Shipping preparation area', category: 'shipping_prep' as const, takenAt: '2024-01-15T14:45:00Z' },
    ];

    // Sample shipping labels
    const sampleShippingLabels = [
      { type: 'main_label' as const, status: 'approved' as const, url: '/labels/main_label.pdf', notes: 'All information verified' },
      { type: 'care_label' as const, status: 'approved' as const, url: '/labels/care_label.pdf' },
      { type: 'size_label' as const, status: 'approved' as const, url: '/labels/size_label.pdf' },
      { type: 'barcode' as const, status: 'pending' as const, notes: 'Pending final SKU confirmation' },
    ];

    // Sample quality checks
    const sampleQualityChecks = [
      { checkType: 'Final Visual Inspection', result: 'pass' as const, details: 'All items meet visual quality standards', inspector: 'Alice Johnson', checkedAt: '2024-01-15T15:00:00Z' },
      { checkType: 'Packaging Material Quality', result: 'pass' as const, details: 'Materials meet specifications', inspector: 'Bob Wilson', checkedAt: '2024-01-15T15:15:00Z' },
      { checkType: 'Label Accuracy Check', result: 'conditional' as const, details: 'Minor adjustments needed for barcode placement', inspector: 'Carol Davis', checkedAt: '2024-01-15T15:30:00Z' },
    ];

    return {
      lot: {
        id: lot.id,
        styleRef: lot.styleRef,
        quantity: lot.quantityTotal,
        factory: {
          name: lot.factory?.name || 'Unknown Factory',
          location: `${lot.factory?.city || 'Unknown'}, ${lot.factory?.country || 'Unknown'}`
        }
      },
      inspection: {
        date: latestInspection.startedAt || latestInspection.createdAt,
        inspector: 'Inspector Name', // You might want to add inspector information to the inspection entity
        status: lot.status.toLowerCase()
      },
      packaging: {
        status: completionPercentage >= 90 ? 'ready' : completionPercentage >= 70 ? 'pending' : 'issues',
        completedChecks: completedItems,
        totalChecks: totalItems,
        completionPercentage,
        readinessDate: completionPercentage >= 90 ? '2024-01-16T09:00:00Z' : undefined
      },
      checklist: sampleChecklist,
      packagingPhotos: params.includePackagingPhotos !== false ? samplePhotos : [],
      shippingLabels: params.includeShippingLabels !== false ? sampleShippingLabels : [],
      qualityChecks: sampleQualityChecks,
      finalApproval,
      shipmentReadiness: {
        estimatedShipDate: '2024-01-17T10:00:00Z',
        carrier: 'FedEx International',
        trackingNumber: completionPercentage >= 90 ? 'FX123456789' : undefined
      },
      comments: latestApproval?.note
    };
  }

  private renderExecutiveQualitySummaryTemplate(data: ExecutiveQualitySummaryData, language: ReportLanguage): string {
    const t = this.getTranslations(language);

    const formatNumber = (num: number) => num.toLocaleString();
    const getPerformanceColor = (performance: string) => {
      switch (performance) {
        case 'good': return '#22c55e';
        case 'average': return '#f59e0b';
        case 'poor': return '#ef4444';
        default: return '#6b7280';
      }
    };

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>${t.title}</title>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: white;
            color: #1f2937;
            line-height: 1.6;
            padding: 20px;
          }

          .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
          }

          .header-left h1 {
            font-size: 28px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 8px;
          }

          .period {
            color: #6b7280;
            font-size: 16px;
          }

          .client-info {
            text-align: right;
          }

          .client-name {
            font-size: 20px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 4px;
          }

          .kpi-section {
            margin-bottom: 40px;
          }

          .section-title {
            font-size: 20px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 8px;
          }

          .section-icon {
            width: 24px;
            height: 24px;
            background: #3b82f6;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            color: white;
          }

          .kpi-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
          }

          .kpi-card {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border: 1px solid #e2e8f0;
            padding: 24px;
            border-radius: 12px;
            text-align: center;
            position: relative;
            overflow: hidden;
          }

          .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #3b82f6, #1d4ed8);
          }

          .kpi-value {
            font-size: 32px;
            font-weight: 700;
            color: #1d4ed8;
            margin-bottom: 8px;
            display: block;
          }

          .kpi-label {
            font-size: 14px;
            color: #64748b;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }

          .content-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
          }

          .content-card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 24px;
          }

          .defect-item, .supplier-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #f3f4f6;
          }

          .defect-item:last-child, .supplier-item:last-child {
            border-bottom: none;
          }

          .defect-name, .supplier-name {
            font-weight: 500;
            color: #374151;
          }

          .defect-stats, .supplier-stats {
            text-align: right;
            font-size: 14px;
          }

          .defect-count {
            font-weight: 600;
            color: #dc2626;
          }

          .defect-percentage {
            color: #6b7280;
            font-size: 12px;
          }

          .performance-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
          }

          .supplier-defect-rate {
            font-weight: 600;
            color: #374151;
          }

          .insights-section {
            margin-bottom: 30px;
          }

          .insights-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
          }

          .insight-item {
            background: #fefce8;
            border: 1px solid #fde047;
            border-radius: 8px;
            padding: 16px;
            font-size: 14px;
            line-height: 1.5;
          }

          .coverage-section {
            background: #f8fafc;
            border-radius: 12px;
            padding: 24px;
          }

          .coverage-stats {
            display: flex;
            justify-content: space-around;
            text-align: center;
          }

          .coverage-item {
            flex: 1;
          }

          .coverage-number {
            font-size: 24px;
            font-weight: 700;
            color: #059669;
            display: block;
            margin-bottom: 4px;
          }

          .coverage-label {
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }

          @media print {
            body { padding: 0; }
            .header { margin-bottom: 30px; }
            .kpi-section { margin-bottom: 30px; }
            .content-grid { margin-bottom: 30px; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="header-left">
            <h1>${t.title}</h1>
            <div class="period">${t.period}: ${data.period.startDate} - ${data.period.endDate}</div>
          </div>
          <div class="client-info">
            <div class="client-name">${data.client.name}</div>
          </div>
        </div>

        <div class="kpi-section">
          <h2 class="section-title">
            <span class="section-icon">📊</span>
            ${t.keyMetrics}
          </h2>
          <div class="kpi-grid">
            <div class="kpi-card">
              <span class="kpi-value">${data.kpis.averageDefectRate}%</span>
              <div class="kpi-label">${t.defectRate}</div>
            </div>
            <div class="kpi-card">
              <span class="kpi-value">${data.kpis.firstPassYield}%</span>
              <div class="kpi-label">${t.firstPassYield}</div>
            </div>
            <div class="kpi-card">
              <span class="kpi-value">${data.kpis.averageLeadTime}</span>
              <div class="kpi-label">${t.avgLeadTime} (${t.days})</div>
            </div>
          </div>
        </div>

        <div class="content-grid">
          <div class="content-card">
            <h2 class="section-title">
              <span class="section-icon">⚠️</span>
              ${t.topDefects}
            </h2>
            ${data.topDefects.map(defect => `
              <div class="defect-item">
                <div class="defect-name">${defect.name}</div>
                <div class="defect-stats">
                  <div class="defect-count">${defect.count}</div>
                  <div class="defect-percentage">${Math.round(defect.percentage)}%</div>
                </div>
              </div>
            `).join('')}
          </div>

          <div class="content-card">
            <h2 class="section-title">
              <span class="section-icon">🏭</span>
              ${t.supplierPerformance}
            </h2>
            ${data.supplierPerformance.map(supplier => `
              <div class="supplier-item">
                <div class="supplier-name">
                  <span class="performance-indicator" style="background-color: ${getPerformanceColor(supplier.performance)}"></span>
                  ${supplier.name}
                </div>
                <div class="supplier-stats">
                  <div class="supplier-defect-rate">${supplier.defectRate.toFixed(1)}%</div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <div class="insights-section">
          <h2 class="section-title">
            <span class="section-icon">💡</span>
            ${t.keyInsights}
          </h2>
          <div class="insights-grid">
            ${data.insights.map(insight => `
              <div class="insight-item">${insight}</div>
            `).join('')}
          </div>
        </div>

        <div class="coverage-section">
          <h2 class="section-title">
            <span class="section-icon">📈</span>
            ${t.coverageStats}
          </h2>
          <div class="coverage-stats">
            <div class="coverage-item">
              <span class="coverage-number">${formatNumber(data.coverageStats.purchaseOrders)}</span>
              <div class="coverage-label">${t.purchaseOrders}</div>
            </div>
            <div class="coverage-item">
              <span class="coverage-number">${formatNumber(data.coverageStats.styles)}</span>
              <div class="coverage-label">${t.styles}</div>
            </div>
            <div class="coverage-item">
              <span class="coverage-number">${formatNumber(data.coverageStats.totalQuantity)}</span>
              <div class="coverage-label">${t.totalQuantity} (${t.units})</div>
            </div>
          </div>
        </div>
      </body>
      </html>
    `;
  }

  private renderLotInspectionReportTemplate(data: LotInspectionReportData, language: ReportLanguage): string {
    const t = this.getTranslations(language);

    const formatDate = (dateString: string) => {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    };

    const getSeverityColor = (severity: string) => {
      switch (severity) {
        case 'critical': return '#dc2626';
        case 'major': return '#ea580c';
        case 'minor': return '#ca8a04';
        default: return '#6b7280';
      }
    };

    const getDecisionColor = (decision: string) => {
      switch (decision) {
        case 'approved': return '#16a34a';
        case 'rejected': return '#dc2626';
        case 'correction_required': return '#ea580c';
        default: return '#6b7280';
      }
    };

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>${t.lotInspectionReport}</title>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: white;
            color: #1f2937;
            line-height: 1.6;
            padding: 20px;
          }

          .header {
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e5e7eb;
          }

          .header h1 {
            font-size: 28px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 8px;
          }

          .lot-id {
            font-size: 16px;
            color: #6b7280;
            font-weight: 500;
          }

          .section {
            margin-bottom: 30px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
            overflow: hidden;
          }

          .section-header {
            background: #f8fafc;
            padding: 16px 20px;
            border-bottom: 1px solid #e2e8f0;
          }

          .section-title {
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
          }

          .section-content {
            padding: 20px;
          }

          .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
          }

          .info-item {
            display: flex;
            flex-direction: column;
          }

          .info-label {
            font-size: 12px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
          }

          .info-value {
            font-size: 16px;
            color: #111827;
            font-weight: 500;
          }

          .defects-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
          }

          .defects-table th,
          .defects-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
          }

          .defects-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #374151;
            font-size: 14px;
          }

          .defects-table td {
            font-size: 14px;
            color: #6b7280;
          }

          .severity-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            color: white;
            text-transform: capitalize;
          }

          .decision-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            color: white;
            text-transform: capitalize;
          }

          .measurements-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 14px;
          }

          .measurements-table th,
          .measurements-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
          }

          .measurements-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #374151;
          }

          .status-pass {
            color: #16a34a;
            font-weight: 600;
          }

          .status-fail {
            color: #dc2626;
            font-weight: 600;
          }

          .no-data {
            text-align: center;
            color: #9ca3af;
            font-style: italic;
            padding: 40px;
          }

          .photos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
          }

          .photo-item {
            text-align: center;
          }

          .photo-placeholder {
            width: 100%;
            height: 150px;
            background: #f3f4f6;
            border: 2px dashed #d1d5db;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            color: #6b7280;
            font-size: 14px;
          }

          .comments-box {
            background: #f8fafc;
            border-left: 4px solid #3b82f6;
            padding: 16px;
            border-radius: 0 8px 8px 0;
            font-style: italic;
            color: #374151;
          }

          @media print {
            body { padding: 0; }
            .section { box-shadow: none; border: 1px solid #e2e8f0; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>${t.title}</h1>
          <p class="lot-id">Lot ID: ${data.lot.id}</p>
        </div>

        <!-- Lot Information Section -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.lotInformation}</h2>
          </div>
          <div class="section-content">
            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">${t.styleRef}</div>
                <div class="info-value">${data.lot.styleRef}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.quantity}</div>
                <div class="info-value">${data.lot.quantity.toLocaleString()} ${t.units}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.factory}</div>
                <div class="info-value">${data.lot.factory.name}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.location}</div>
                <div class="info-value">${data.lot.factory.location}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Inspection Details Section -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.inspectionDetails}</h2>
          </div>
          <div class="section-content">
            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">${t.inspectionDate}</div>
                <div class="info-value">${formatDate(data.inspection.date)}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.inspector}</div>
                <div class="info-value">${data.inspection.inspector}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.duration}</div>
                <div class="info-value">${data.inspection.duration} ${t.minutes}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.status}</div>
                <div class="info-value">${data.inspection.status}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Quality Defects Section -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.qualityDefects}</h2>
          </div>
          <div class="section-content">
            ${data.defects && data.defects.length > 0 ? `
              <table class="defects-table">
                <thead>
                  <tr>
                    <th>${t.defectType}</th>
                    <th>${t.count}</th>
                    <th>${t.severity}</th>
                  </tr>
                </thead>
                <tbody>
                  ${data.defects.map(defect => `
                    <tr>
                      <td>${defect.type}</td>
                      <td>${defect.count}</td>
                      <td>
                        <span class="severity-badge" style="background-color: ${getSeverityColor(defect.severity)}">
                          ${defect.severity}
                        </span>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            ` : `
              <div class="no-data">${t.noDefects}</div>
            `}
          </div>
        </div>

        <!-- Measurements Section -->
        ${data.measurements && data.measurements.length > 0 ? `
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.measurements}</h2>
          </div>
          <div class="section-content">
            <table class="measurements-table">
              <thead>
                <tr>
                  <th>${t.measurementPoint}</th>
                  <th>${t.specification}</th>
                  <th>${t.tolerance}</th>
                  <th>${t.measured}</th>
                  <th>${t.deviation}</th>
                  <th>${t.result}</th>
                </tr>
              </thead>
              <tbody>
                ${data.measurements.map(measurement => `
                  <tr>
                    <td>${measurement.point}</td>
                    <td>${measurement.specification}</td>
                    <td>${measurement.tolerance}</td>
                    <td>${measurement.measured}</td>
                    <td>${measurement.deviation}%</td>
                    <td class="${measurement.status === 'pass' ? 'status-pass' : 'status-fail'}">
                      ${measurement.status === 'pass' ? t.pass : t.fail}
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
        ` : `
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.measurements}</h2>
          </div>
          <div class="section-content">
            <div class="no-data">${t.noMeasurements}</div>
          </div>
        </div>
        `}

        <!-- Photos Section -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.inspectionPhotos}</h2>
          </div>
          <div class="section-content">
            ${data.photos && data.photos.length > 0 ? `
              <div class="photos-grid">
                ${data.photos.map(photo => `
                  <div class="photo-item">
                    <div class="photo-placeholder">
                      📷 ${photo.caption || 'Inspection Photo'}
                    </div>
                  </div>
                `).join('')}
              </div>
            ` : `
              <div class="no-data">${t.noPhotos}</div>
            `}
          </div>
        </div>

        <!-- Final Decision Section -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.finalDecision}</h2>
          </div>
          <div class="section-content">
            <div style="text-align: center; margin-bottom: 20px;">
              <span class="decision-badge" style="background-color: ${getDecisionColor(data.decision)}">
                ${data.decision.replace('_', ' ').toUpperCase()}
              </span>
            </div>

            ${data.comments ? `
              <div>
                <h3 style="margin-bottom: 10px; color: #374151;">${t.comments}</h3>
                <div class="comments-box">
                  ${data.comments}
                </div>
              </div>
            ` : `
              <div class="no-data">${t.noComments}</div>
            `}
          </div>
        </div>
      </body>
      </html>
    `;
  }

  private getTranslations(language: ReportLanguage) {
    const labels = {
      en: {
        // Executive Quality Summary
        title: 'Executive Quality Summary',
        period: 'Period',
        keyMetrics: 'Key Quality Metrics',
        defectRate: 'Defect Rate',
        firstPassYield: 'First Pass Yield',
        avgLeadTime: 'Avg Lead Time',
        days: 'days',
        topDefects: 'Top Quality Issues',
        supplierPerformance: 'Supplier Performance',
        keyInsights: 'Key Insights',
        coverageStats: 'Coverage Statistics',
        purchaseOrders: 'Purchase Orders',
        styles: 'Styles Inspected',
        totalQuantity: 'Total Quantity',
        units: 'units',
        supplier: 'Supplier',
        defectType: 'Defect Type',
        count: 'Count',
        percentage: 'Percentage',

        // Lot Inspection Report
        lotInspectionReport: 'Lot Inspection Report',
        lotInformation: 'Lot Information',
        inspectionDetails: 'Inspection Details',
        qualityDefects: 'Quality Defects',
        measurements: 'Measurements',
        inspectionPhotos: 'Inspection Photos',
        finalDecision: 'Final Decision',
        comments: 'Comments',
        styleRef: 'Style Reference',
        styleReference: 'Style Reference',
        quantity: 'Quantity',
        factory: 'Factory',
        location: 'Location',
        inspectionDate: 'Inspection Date',
        inspector: 'Inspector',
        duration: 'Duration',
        status: 'Status',
        severity: 'Severity',
        measurementPoint: 'Measurement Point',
        specification: 'Specification',
        tolerance: 'Tolerance',
        measured: 'Measured',
        deviation: 'Deviation',
        result: 'Result',
        noDefects: 'No defects found during inspection',
        noMeasurements: 'No measurements recorded',
        noPhotos: 'No photos available',
        noComments: 'No additional comments',
        minutes: 'minutes',
        pass: 'Pass',
        fail: 'Fail',

        // Measurement Compliance Sheet
        measurementComplianceSheet: 'Measurement Compliance Sheet',
        technicalQualityReport: 'Technical Quality Report',
        complianceSummary: 'Compliance Summary',
        totalMeasurements: 'Total Measurements',
        passedMeasurements: 'Passed Measurements',
        failedMeasurements: 'Failed Measurements',
        overallCompliance: 'Overall Compliance',
        detailedMeasurements: 'Detailed Measurements',
        sampleId: 'Sample ID',
        notes: 'Notes',
        approved: 'APPROVED',
        conditionalApproval: 'CONDITIONAL APPROVAL',
        rejected: 'REJECTED',
        lotId: 'Lot ID',

        // Packaging & Readiness Report
        packagingReadinessReport: 'Packaging & Readiness Report',
        packagingStatus: 'Packaging Status',
        readinessDate: 'Readiness Date',
        completionPercentage: 'Completion Percentage',
        completedChecks: 'Completed Checks',
        totalChecks: 'Total Checks',
        packagingChecklist: 'Packaging Checklist',
        category: 'Category',
        checkItem: 'Check Item',
        checkedBy: 'Checked By',
        checkedAt: 'Checked At',
        packagingPhotos: 'Packaging Photos',
        shippingLabels: 'Shipping Labels',
        labelType: 'Label Type',
        qualityChecks: 'Quality Checks',
        checkType: 'Check Type',
        details: 'Details',
        shipmentReadiness: 'Shipment Readiness',
        estimatedShipDate: 'Estimated Ship Date',
        carrier: 'Carrier',
        trackingNumber: 'Tracking Number',
        ready: 'READY',
        pending: 'PENDING',
        issues: 'ISSUES',
        mainLabel: 'Main Label',
        careLabel: 'Care Label',
        sizeLabel: 'Size Label',
        barcode: 'Barcode',
        conditional: 'Conditional',
        completed: 'Completed',
        items: 'Item',
        photos: 'Photo',
        shipDate: 'Ship Date',
        shippingInformation: 'Shipping Information',
        actualShipDate: 'Actual Ship Date',

        // DPP Summary Report
        dppSummaryReport: 'DPP Summary Report',
        digitalProductPassport: 'Digital Product Passport',
        dppId: 'DPP ID',
        version: 'Version',
        publishedAt: 'Published At',
        expiresAt: 'Expires At',
        productInformation: 'Product Information',
        productName: 'Product Name',
        season: 'Season',
        composition: 'Composition',
        material: 'Material',
        origin: 'Origin',
        careInstructions: 'Care Instructions',
        washingTemp: 'Washing Temperature',
        drying: 'Drying',
        ironing: 'Ironing',
        sustainabilityMetrics: 'Sustainability Metrics',
        carbonFootprint: 'Carbon Footprint',
        waterUsage: 'Water Usage',
        recyclability: 'Recyclability',
        carbonFootprintBreakdown: 'Carbon Footprint Breakdown',
        waterUsageBreakdown: 'Water Usage Breakdown',
        supplyChain: 'Supply Chain',
        tier: 'Tier',
        sustainabilityScore: 'Sustainability Score',
        compliance: 'Compliance',
        regulations: 'Regulations',
        regulation: 'Regulation',
        region: 'Region',
        validatedAt: 'Validated At',
        testResults: 'Test Results',
        testType: 'Test Type',
        standard: 'Standard',
        laboratory: 'Laboratory',
        testedAt: 'Tested At',
        traceability: 'Traceability',
        batchNumber: 'Batch Number',
        productionDate: 'Production Date',
        factoryLocation: 'Factory Location',
        productionTimeline: 'Production Timeline',
        circularity: 'Circularity',
        designForCircularity: 'Design for Circularity',
        points: 'points',
        endOfLifeOptions: 'End of Life Options',
        impact: 'Impact',
        recommendations: 'Recommendations',
        issuer: 'Issuer',
        valid: 'Valid',
        certificateNumber: 'Certificate Number',
        digitalAccess: 'Digital Access',
        scanForDetails: 'Scan for Details',
        scanWithPhone: 'Scan with your phone to access full product information',
        accessibilityFeatures: 'Accessibility Features',
        enabled: 'Enabled',
        disabled: 'Disabled',
        digitalTwin: 'Digital Twin',
        available: 'Available',
        notAvailable: 'Not Available',
        mobileApp: 'Mobile App',
        supportedLanguages: 'Supported Languages',
        description: 'Description',
        role: 'Role',
        certifications: 'Certifications'
      },
      pt: {
        // Executive Quality Summary
        title: 'Resumo Executivo de Qualidade',
        period: 'Período',
        keyMetrics: 'Métricas Principais de Qualidade',
        defectRate: 'Taxa de Defeitos',
        firstPassYield: 'Taxa de Aprovação',
        avgLeadTime: 'Tempo Médio',
        days: 'dias',
        topDefects: 'Principais Problemas de Qualidade',
        supplierPerformance: 'Desempenho dos Fornecedores',
        keyInsights: 'Principais Insights',
        coverageStats: 'Estatísticas de Cobertura',
        purchaseOrders: 'Pedidos de Compra',
        styles: 'Estilos Inspecionados',
        totalQuantity: 'Quantidade Total',
        units: 'unidades',
        supplier: 'Fornecedor',
        defectType: 'Tipo de Defeito',
        count: 'Contagem',
        percentage: 'Porcentagem',

        // Lot Inspection Report
        lotInspectionReport: 'Relatório de Inspeção de Lote',
        lotInformation: 'Informações do Lote',
        inspectionDetails: 'Detalhes da Inspeção',
        qualityDefects: 'Defeitos de Qualidade',
        measurements: 'Medições',
        inspectionPhotos: 'Fotos da Inspeção',
        finalDecision: 'Decisão Final',
        comments: 'Comentários',
        styleRef: 'Referência do Estilo',
        styleReference: 'Referência do Estilo',
        quantity: 'Quantidade',
        factory: 'Fábrica',
        location: 'Localização',
        inspectionDate: 'Data da Inspeção',
        inspector: 'Inspetor',
        duration: 'Duração',
        status: 'Status',
        severity: 'Severidade',
        measurementPoint: 'Ponto de Medição',
        specification: 'Especificação',
        tolerance: 'Tolerância',
        measured: 'Medido',
        deviation: 'Desvio',
        result: 'Resultado',
        noDefects: 'Nenhum defeito encontrado durante a inspeção',
        noMeasurements: 'Nenhuma medição registrada',
        noPhotos: 'Nenhuma foto disponível',
        noComments: 'Nenhum comentário adicional',
        minutes: 'minutos',
        pass: 'Aprovado',
        fail: 'Reprovado',

        // Measurement Compliance Sheet
        measurementComplianceSheet: 'Planilha de Conformidade de Medições',
        technicalQualityReport: 'Relatório Técnico de Qualidade',
        complianceSummary: 'Resumo de Conformidade',
        totalMeasurements: 'Total de Medições',
        passedMeasurements: 'Medições Aprovadas',
        failedMeasurements: 'Medições Reprovadas',
        overallCompliance: 'Conformidade Geral',
        detailedMeasurements: 'Medições Detalhadas',
        sampleId: 'ID da Amostra',
        notes: 'Observações',
        approved: 'APROVADO',
        conditionalApproval: 'APROVAÇÃO CONDICIONAL',
        rejected: 'REJEITADO',
        lotId: 'ID do Lote',

        // Packaging & Readiness Report
        packagingReadinessReport: 'Relatório de Embalagem e Preparação',
        packagingStatus: 'Status da Embalagem',
        readinessDate: 'Data de Preparação',
        completionPercentage: 'Porcentagem de Conclusão',
        completedChecks: 'Verificações Concluídas',
        totalChecks: 'Total de Verificações',
        packagingChecklist: 'Lista de Verificação de Embalagem',
        category: 'Categoria',
        checkItem: 'Item de Verificação',
        checkedBy: 'Verificado por',
        checkedAt: 'Verificado em',
        packagingPhotos: 'Fotos da Embalagem',
        shippingLabels: 'Etiquetas de Envio',
        labelType: 'Tipo de Etiqueta',
        qualityChecks: 'Verificações de Qualidade',
        checkType: 'Tipo de Verificação',
        details: 'Detalhes',
        shipmentReadiness: 'Preparação para Envio',
        estimatedShipDate: 'Data Estimada de Envio',
        carrier: 'Transportadora',
        trackingNumber: 'Número de Rastreamento',
        ready: 'PRONTO',
        pending: 'PENDENTE',
        issues: 'PROBLEMAS',
        mainLabel: 'Etiqueta Principal',
        careLabel: 'Etiqueta de Cuidados',
        sizeLabel: 'Etiqueta de Tamanho',
        barcode: 'Código de Barras',
        conditional: 'Condicional',
        completed: 'Completo',
        items: 'Item',
        photos: 'Foto',
        shipDate: 'Data de Envio',
        shippingInformation: 'Informações de Envio',
        actualShipDate: 'Data Real de Envio',

        // DPP Summary Report
        dppSummaryReport: 'Relatório de Resumo do DPP',
        digitalProductPassport: 'Passaporte Digital do Produto',
        dppId: 'ID do DPP',
        version: 'Versão',
        publishedAt: 'Publicado em',
        expiresAt: 'Expira em',
        productInformation: 'Informações do Produto',
        productName: 'Nome do Produto',
        season: 'Estação',
        composition: 'Composição',
        material: 'Material',
        origin: 'Origem',
        careInstructions: 'Instruções de Cuidado',
        washingTemp: 'Temperatura de Lavagem',
        drying: 'Secagem',
        ironing: 'Passar Ferro',
        sustainabilityMetrics: 'Métricas de Sustentabilidade',
        carbonFootprint: 'Pegada de Carbono',
        waterUsage: 'Uso de Água',
        recyclability: 'Reciclabilidade',
        carbonFootprintBreakdown: 'Detalhamento da Pegada de Carbono',
        waterUsageBreakdown: 'Detalhamento do Uso de Água',
        supplyChain: 'Cadeia de Suprimentos',
        tier: 'Nível',
        sustainabilityScore: 'Pontuação de Sustentabilidade',
        compliance: 'Conformidade',
        regulations: 'Regulamentos',
        regulation: 'Regulamento',
        region: 'Região',
        validatedAt: 'Validado em',
        testResults: 'Resultados de Testes',
        testType: 'Tipo de Teste',
        standard: 'Padrão',
        laboratory: 'Laboratório',
        testedAt: 'Testado em',
        traceability: 'Rastreabilidade',
        batchNumber: 'Número do Lote',
        productionDate: 'Data de Produção',
        factoryLocation: 'Localização da Fábrica',
        productionTimeline: 'Cronograma de Produção',
        circularity: 'Circularidade',
        designForCircularity: 'Design para Circularidade',
        points: 'pontos',
        endOfLifeOptions: 'Opções de Fim de Vida',
        impact: 'Impacto',
        recommendations: 'Recomendações',
        issuer: 'Emissor',
        valid: 'Válido',
        certificateNumber: 'Número do Certificado',
        digitalAccess: 'Acesso Digital',
        scanForDetails: 'Escanear para Detalhes',
        scanWithPhone: 'Escaneie com seu telefone para acessar informações completas do produto',
        accessibilityFeatures: 'Recursos de Acessibilidade',
        enabled: 'Habilitado',
        disabled: 'Desabilitado',
        digitalTwin: 'Gêmeo Digital',
        available: 'Disponível',
        notAvailable: 'Não Disponível',
        mobileApp: 'Aplicativo Móvel',
        supportedLanguages: 'Idiomas Suportados',
        description: 'Descrição',
        role: 'Função',
        certifications: 'Certificações'
      },
      es: {
        // Executive Quality Summary
        title: 'Resumen Ejecutivo de Calidad',
        period: 'Período',
        keyMetrics: 'Métricas Clave de Calidad',
        defectRate: 'Tasa de Defectos',
        firstPassYield: 'Rendimiento Primera Pasada',
        avgLeadTime: 'Tiempo Promedio',
        days: 'días',
        topDefects: 'Principales Problemas de Calidad',
        supplierPerformance: 'Rendimiento de Proveedores',
        keyInsights: 'Principales Insights',
        coverageStats: 'Estadísticas de Cobertura',
        purchaseOrders: 'Órdenes de Compra',
        styles: 'Estilos Inspeccionados',
        totalQuantity: 'Cantidad Total',
        units: 'unidades',
        supplier: 'Proveedor',
        defectType: 'Tipo de Defecto',
        count: 'Conteo',
        percentage: 'Porcentaje',

        // Lot Inspection Report
        lotInspectionReport: 'Informe de Inspección de Lote',
        lotInformation: 'Información del Lote',
        inspectionDetails: 'Detalles de la Inspección',
        qualityDefects: 'Defectos de Calidad',
        measurements: 'Mediciones',
        inspectionPhotos: 'Fotos de la Inspección',
        finalDecision: 'Decisión Final',
        comments: 'Comentarios',
        styleRef: 'Referencia del Estilo',
        styleReference: 'Referencia del Estilo',
        quantity: 'Cantidad',
        factory: 'Fábrica',
        location: 'Ubicación',
        inspectionDate: 'Fecha de Inspección',
        inspector: 'Inspector',
        duration: 'Duración',
        status: 'Estado',
        severity: 'Severidad',
        measurementPoint: 'Punto de Medición',
        specification: 'Especificación',
        tolerance: 'Tolerancia',
        measured: 'Medido',
        deviation: 'Desviación',
        result: 'Resultado',
        noDefects: 'No se encontraron defectos durante la inspección',
        noMeasurements: 'No hay mediciones registradas',
        noPhotos: 'No hay fotos disponibles',
        noComments: 'Sin comentarios adicionales',
        minutes: 'minutos',
        pass: 'Aprobar',
        fail: 'Fallar',

        // Measurement Compliance Sheet
        measurementComplianceSheet: 'Hoja de Cumplimiento de Mediciones',
        technicalQualityReport: 'Informe Técnico de Calidad',
        complianceSummary: 'Resumen de Cumplimiento',
        totalMeasurements: 'Total de Mediciones',
        passedMeasurements: 'Mediciones Aprobadas',
        failedMeasurements: 'Mediciones Fallidas',
        overallCompliance: 'Cumplimiento General',
        detailedMeasurements: 'Mediciones Detalladas',
        sampleId: 'ID de Muestra',
        notes: 'Notas',
        approved: 'APROBADO',
        conditionalApproval: 'APROBACIÓN CONDICIONAL',
        rejected: 'RECHAZADO',
        lotId: 'ID de Lote',

        // Packaging & Readiness Report
        packagingReadinessReport: 'Informe de Embalaje y Preparación',
        packagingStatus: 'Estado del Embalaje',
        readinessDate: 'Fecha de Preparación',
        completionPercentage: 'Porcentaje de Finalización',
        completedChecks: 'Verificaciones Completadas',
        totalChecks: 'Total de Verificaciones',
        packagingChecklist: 'Lista de Verificación de Embalaje',
        category: 'Categoría',
        checkItem: 'Elemento de Verificación',
        checkedBy: 'Verificado por',
        checkedAt: 'Verificado en',
        packagingPhotos: 'Fotos del Embalaje',
        shippingLabels: 'Etiquetas de Envío',
        labelType: 'Tipo de Etiqueta',
        qualityChecks: 'Verificaciones de Calidad',
        checkType: 'Tipo de Verificación',
        details: 'Detalles',
        shipmentReadiness: 'Preparación para Envío',
        estimatedShipDate: 'Fecha Estimada de Envío',
        carrier: 'Transportista',
        trackingNumber: 'Número de Seguimiento',
        ready: 'LISTO',
        pending: 'PENDIENTE',
        issues: 'PROBLEMAS',
        mainLabel: 'Etiqueta Principal',
        careLabel: 'Etiqueta de Cuidado',
        sizeLabel: 'Etiqueta de Talla',
        barcode: 'Código de Barras',
        conditional: 'Condicional',
        completed: 'Completado',
        items: 'Elemento',
        photos: 'Foto',
        shipDate: 'Fecha de Envío',
        shippingInformation: 'Información de Envío',
        actualShipDate: 'Fecha Real de Envío',

        // DPP Summary Report
        dppSummaryReport: 'Informe de Resumen DPP',
        digitalProductPassport: 'Pasaporte Digital del Producto',
        dppId: 'ID del DPP',
        version: 'Versión',
        publishedAt: 'Publicado en',
        expiresAt: 'Expira en',
        productInformation: 'Información del Producto',
        productName: 'Nombre del Producto',
        season: 'Temporada',
        composition: 'Composición',
        material: 'Material',
        origin: 'Origen',
        careInstructions: 'Instrucciones de Cuidado',
        washingTemp: 'Temperatura de Lavado',
        drying: 'Secado',
        ironing: 'Planchado',
        sustainabilityMetrics: 'Métricas de Sostenibilidad',
        carbonFootprint: 'Huella de Carbono',
        waterUsage: 'Uso del Agua',
        recyclability: 'Reciclabilidad',
        carbonFootprintBreakdown: 'Desglose de la Huella de Carbono',
        waterUsageBreakdown: 'Desglose del Uso del Agua',
        supplyChain: 'Cadena de Suministro',
        tier: 'Nivel',
        sustainabilityScore: 'Puntuación de Sostenibilidad',
        compliance: 'Cumplimiento',
        regulations: 'Regulaciones',
        regulation: 'Regulación',
        region: 'Región',
        validatedAt: 'Validado en',
        testResults: 'Resultados de Pruebas',
        testType: 'Tipo de Prueba',
        standard: 'Estándar',
        laboratory: 'Laboratorio',
        testedAt: 'Probado en',
        traceability: 'Trazabilidad',
        batchNumber: 'Número de Lote',
        productionDate: 'Fecha de Producción',
        factoryLocation: 'Ubicación de la Fábrica',
        productionTimeline: 'Cronología de Producción',
        circularity: 'Circularidad',
        designForCircularity: 'Diseño para la Circularidad',
        points: 'puntos',
        endOfLifeOptions: 'Opciones de Fin de Vida',
        impact: 'Impacto',
        recommendations: 'Recomendaciones',
        issuer: 'Emisor',
        valid: 'Válido',
        certificateNumber: 'Número de Certificado',
        digitalAccess: 'Acceso Digital',
        scanForDetails: 'Escanear para Detalles',
        scanWithPhone: 'Escanea con tu teléfono para acceder a la información completa del producto',
        accessibilityFeatures: 'Características de Accesibilidad',
        enabled: 'Habilitado',
        disabled: 'Deshabilitado',
        digitalTwin: 'Gemelo Digital',
        available: 'Disponible',
        notAvailable: 'No Disponible',
        mobileApp: 'Aplicación Móvil',
        supportedLanguages: 'Idiomas Soportados',
        description: 'Descripción',
        role: 'Rol',
        certifications: 'Certificaciones'
      }
    };

    return labels[language.toLowerCase() as keyof typeof labels] || labels.en;
  }

  private renderMeasurementComplianceSheetTemplate(data: MeasurementComplianceSheetData, language: ReportLanguage): string {
    const t = this.getTranslations(language);

    const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString();

    return `
      <!DOCTYPE html>
      <html lang="${language.toLowerCase()}">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>${t.measurementComplianceSheet}</title>
        <style>
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }

          body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #374151;
            background: white;
            padding: 30px;
          }

          .header {
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 20px;
          }

          .header h1 {
            color: #1e40af;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 10px;
          }

          .header .subtitle {
            color: #6b7280;
            font-size: 16px;
            font-weight: 500;
          }

          .section {
            margin-bottom: 30px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
          }

          .section-header {
            background: #f8fafc;
            padding: 15px 20px;
            border-bottom: 1px solid #e5e7eb;
          }

          .section-title {
            color: #374151;
            font-size: 18px;
            font-weight: 600;
            margin: 0;
          }

          .section-content {
            padding: 20px;
          }

          .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
          }

          .info-item {
            display: flex;
            flex-direction: column;
          }

          .info-label {
            font-size: 13px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
          }

          .info-value {
            font-size: 16px;
            font-weight: 500;
            color: #111827;
          }

          .measurements-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            margin-top: 20px;
          }

          .measurements-table th,
          .measurements-table td {
            padding: 12px;
            text-align: left;
            border: 1px solid #e5e7eb;
          }

          .measurements-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #374151;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }

          .measurements-table tbody tr:nth-child(even) {
            background-color: #f9fafb;
          }

          .measurements-table tbody tr:hover {
            background-color: #f3f4f6;
          }

          .status-pass {
            color: #16a34a;
            font-weight: 600;
            background: #dcfce7;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            text-transform: uppercase;
            display: inline-block;
          }

          .status-fail {
            color: #dc2626;
            font-weight: 600;
            background: #fecaca;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            text-transform: uppercase;
            display: inline-block;
          }

          .deviation-positive {
            color: #dc2626;
            font-weight: 500;
          }

          .deviation-negative {
            color: #dc2626;
            font-weight: 500;
          }

          .deviation-zero {
            color: #16a34a;
            font-weight: 500;
          }

          .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
          }

          .summary-card {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
          }

          .summary-label {
            font-size: 13px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
          }

          .summary-value {
            font-size: 24px;
            font-weight: 700;
            color: #111827;
          }

          .summary-percentage {
            font-size: 18px;
            font-weight: 600;
            color: #3b82f6;
          }

          .approval-status {
            text-align: center;
            margin: 30px 0;
          }

          .approval-badge {
            display: inline-block;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
          }

          .approval-approved {
            background: #dcfce7;
            color: #16a34a;
            border: 2px solid #16a34a;
          }

          .approval-conditional {
            background: #fef3c7;
            color: #d97706;
            border: 2px solid #d97706;
          }

          .approval-rejected {
            background: #fecaca;
            color: #dc2626;
            border: 2px solid #dc2626;
          }

          .comments-box {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
            font-style: italic;
            color: #6b7280;
          }

          .no-data {
            text-align: center;
            color: #9ca3af;
            font-style: italic;
            padding: 40px;
          }

          @media print {
            body {
              padding: 20px;
            }
            .section {
              break-inside: avoid;
              margin-bottom: 20px;
            }
          }
        </style>
      </head>
      <body>
        <!-- Header -->
        <div class="header">
          <h1>${t.measurementComplianceSheet}</h1>
          <div class="subtitle">${t.technicalQualityReport}</div>
        </div>

        <!-- Lot Information -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.lotInformation}</h2>
          </div>
          <div class="section-content">
            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">${t.lotId}</div>
                <div class="info-value">${data.lot.id}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.styleReference}</div>
                <div class="info-value">${data.lot.styleRef}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.quantity}</div>
                <div class="info-value">${data.lot.quantity.toLocaleString()} ${t.units}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.factory}</div>
                <div class="info-value">${data.lot.factory.name}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.location}</div>
                <div class="info-value">${data.lot.factory.location}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Inspection Information -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.inspectionDetails}</h2>
          </div>
          <div class="section-content">
            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">${t.inspectionDate}</div>
                <div class="info-value">${formatDate(data.inspection.date)}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.inspector}</div>
                <div class="info-value">${data.inspection.inspector}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.status}</div>
                <div class="info-value">${data.inspection.status}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Compliance Summary -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.complianceSummary}</h2>
          </div>
          <div class="section-content">
            <div class="summary-grid">
              <div class="summary-card">
                <div class="summary-label">${t.totalMeasurements}</div>
                <div class="summary-value">${data.summary.totalMeasurements}</div>
              </div>
              <div class="summary-card">
                <div class="summary-label">${t.passedMeasurements}</div>
                <div class="summary-value" style="color: #16a34a;">${data.summary.passedMeasurements}</div>
              </div>
              <div class="summary-card">
                <div class="summary-label">${t.failedMeasurements}</div>
                <div class="summary-value" style="color: #dc2626;">${data.summary.failedMeasurements}</div>
              </div>
              <div class="summary-card">
                <div class="summary-label">${t.overallCompliance}</div>
                <div class="summary-percentage">${data.summary.overallCompliance}%</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Detailed Measurements -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.detailedMeasurements}</h2>
          </div>
          <div class="section-content">
            ${data.measurements && data.measurements.length > 0 ? `
              <table class="measurements-table">
                <thead>
                  <tr>
                    ${data.measurements[0].sampleId ? `<th>${t.sampleId}</th>` : ''}
                    <th>${t.measurementPoint}</th>
                    <th>${t.specification}</th>
                    <th>${t.tolerance}</th>
                    <th>${t.measured}</th>
                    <th>${t.deviation}</th>
                    <th>${t.result}</th>
                    <th>${t.notes}</th>
                  </tr>
                </thead>
                <tbody>
                  ${data.measurements.map(measurement => `
                    <tr>
                      ${measurement.sampleId ? `<td>${measurement.sampleId}</td>` : ''}
                      <td><strong>${measurement.measurementPoint}</strong></td>
                      <td>${measurement.specification.target} ${measurement.specification.unit}</td>
                      <td>${measurement.specification.tolerance}</td>
                      <td>${measurement.measured.value} ${measurement.measured.unit}</td>
                      <td class="${measurement.deviation === 0 ? 'deviation-zero' : (measurement.deviation > 0 ? 'deviation-positive' : 'deviation-negative')}">
                        ${measurement.deviation > 0 ? '+' : ''}${measurement.deviation}%
                      </td>
                      <td>
                        <span class="${measurement.status === 'pass' ? 'status-pass' : 'status-fail'}">
                          ${measurement.status === 'pass' ? t.pass : t.fail}
                        </span>
                      </td>
                      <td>${measurement.notes || '-'}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            ` : `
              <div class="no-data">${t.noMeasurements}</div>
            `}
          </div>
        </div>

        <!-- Approval Status -->
        <div class="approval-status">
          <div class="approval-badge approval-${data.approvalStatus}">
            ${data.approvalStatus === 'approved' ? t.approved :
              data.approvalStatus === 'conditional' ? t.conditionalApproval : t.rejected}
          </div>
        </div>

        <!-- Comments -->
        ${data.comments ? `
          <div class="section">
            <div class="section-header">
              <h2 class="section-title">${t.comments}</h2>
            </div>
            <div class="section-content">
              <div class="comments-box">
                ${data.comments}
              </div>
            </div>
          </div>
        ` : ''}

      </body>
      </html>
    `;
  }

  private renderPackagingReadinessReportTemplate(data: PackagingReadinessReportData, language: ReportLanguage): string {
    const t = this.getTranslations(language);

    const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString();
    const formatDateTime = (dateStr: string) => new Date(dateStr).toLocaleString();

    const getStatusColor = (status: string) => {
      switch (status) {
        case 'ready': return '#16a34a';
        case 'pending': return '#d97706';
        case 'issues': return '#dc2626';
        default: return '#6b7280';
      }
    };

    const getResultColor = (result: string) => {
      switch (result) {
        case 'pass': return '#16a34a';
        case 'conditional': return '#d97706';
        case 'fail': return '#dc2626';
        default: return '#6b7280';
      }
    };

    return `
      <!DOCTYPE html>
      <html lang="${language.toLowerCase()}">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>${t.packagingReadinessReport}</title>
        <style>
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }

          body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #374151;
            background: white;
            padding: 30px;
          }

          .header {
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 20px;
          }

          .header h1 {
            color: #1e40af;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 10px;
          }

          .header .subtitle {
            color: #6b7280;
            font-size: 16px;
            font-weight: 500;
          }

          .section {
            margin-bottom: 30px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
          }

          .section-header {
            background: #f8fafc;
            padding: 20px;
            border-bottom: 1px solid #e5e7eb;
          }

          .section-title {
            font-size: 20px;
            font-weight: 600;
            color: #111827;
            display: flex;
            align-items: center;
            gap: 8px;
          }

          .section-content {
            padding: 20px;
          }

          .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
          }

          .info-item {
            display: flex;
            flex-direction: column;
          }

          .info-label {
            font-size: 12px;
            color: #6b7280;
            font-weight: 500;
            margin-bottom: 4px;
            text-transform: uppercase;
          }

          .info-value {
            font-size: 16px;
            color: #374151;
            font-weight: 600;
          }

          .status-overview {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
          }

          .status-card {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border: 1px solid #e2e8f0;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
          }

          .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 10px;
          }

          .status-ready { background: #dcfce7; color: #166534; }
          .status-pending { background: #fef3c7; color: #92400e; }
          .status-issues { background: #fee2e2; color: #991b1b; }

          .progress-bar {
            width: 100%;
            height: 20px;
            background: #e5e7eb;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
          }

          .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            transition: width 0.3s ease;
          }

          .progress-text {
            margin-top: 8px;
            font-size: 14px;
            font-weight: 600;
            color: #374151;
          }

          .checklist-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
          }

          .checklist-table th,
          .checklist-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
          }

          .checklist-table th {
            background: #f9fafb;
            font-weight: 600;
            color: #374151;
          }

          .checklist-category {
            font-weight: 600;
            color: #1f2937;
            background: #f3f4f6;
          }

          .checklist-item {
            padding-left: 20px;
          }

          .status-completed { color: #16a34a; font-weight: 600; }
          .status-pending { color: #d97706; font-weight: 600; }
          .status-failed { color: #dc2626; font-weight: 600; }

          .photos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
          }

          .photo-item {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
          }

          .photo-placeholder {
            height: 150px;
            background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6b7280;
            font-size: 14px;
          }

          .photo-caption {
            padding: 10px;
            font-size: 12px;
            color: #6b7280;
            background: #f9fafb;
          }

          .labels-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
          }

          .label-item {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 15px;
            background: #f9fafb;
          }

          .label-type {
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 5px;
          }

          .label-status {
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            font-weight: 600;
            display: inline-block;
          }

          .label-approved { background: #dcfce7; color: #166534; }
          .label-pending { background: #fef3c7; color: #92400e; }
          .label-rejected { background: #fee2e2; color: #991b1b; }

          .quality-checks {
            margin-top: 15px;
          }

          .quality-check {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            margin-bottom: 10px;
          }

          .check-result {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
          }

          .result-pass { background: #dcfce7; color: #166534; }
          .result-conditional { background: #fef3c7; color: #92400e; }
          .result-fail { background: #fee2e2; color: #991b1b; }

          .final-approval {
            text-align: center;
            margin: 30px 0;
          }

          .approval-badge {
            display: inline-block;
            padding: 15px 30px;
            border-radius: 25px;
            font-size: 18px;
            font-weight: 700;
            text-transform: uppercase;
          }

          .approval-approved { background: #dcfce7; color: #166534; }
          .approval-conditional { background: #fef3c7; color: #92400e; }
          .approval-rejected { background: #fee2e2; color: #991b1b; }

          .shipment-info {
            background: #f0f9ff;
            border: 1px solid #7dd3fc;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
          }

          .shipment-title {
            font-size: 16px;
            font-weight: 600;
            color: #0c4a6e;
            margin-bottom: 10px;
          }

          .shipment-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
          }

          .comments-box {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 15px;
            font-style: italic;
            color: #6b7280;
          }

          .no-data {
            text-align: center;
            color: #6b7280;
            font-style: italic;
            padding: 20px;
          }
        </style>
      </head>
      <body>
        <!-- Header -->
        <div class="header">
          <h1>${t.packagingReadinessReport}</h1>
          <div class="subtitle">${t.lotId}: ${data.lot.id} - ${data.lot.styleRef}</div>
        </div>

        <!-- Lot Information -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.lotInformation}</h2>
          </div>
          <div class="section-content">
            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">${t.styleReference}</div>
                <div class="info-value">${data.lot.styleRef}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.quantity}</div>
                <div class="info-value">${data.lot.quantity.toLocaleString()} ${t.units}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.factory}</div>
                <div class="info-value">${data.lot.factory.name}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.location}</div>
                <div class="info-value">${data.lot.factory.location}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.inspectionDate}</div>
                <div class="info-value">${formatDate(data.inspection.date)}</div>
              </div>
              <div class="info-item">
                <div class="info-label">${t.inspector}</div>
                <div class="info-value">${data.inspection.inspector}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Packaging Status Overview -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.packagingStatus}</h2>
          </div>
          <div class="section-content">
            <div class="status-overview">
              <div class="status-card">
                <div class="status-badge status-${data.packaging.status}">
                  ${data.packaging.status === 'ready' ? t.ready :
                    data.packaging.status === 'pending' ? t.pending : t.issues}
                </div>
                <div class="progress-bar">
                  <div class="progress-fill" style="width: ${data.packaging.completionPercentage}%"></div>
                </div>
                <div class="progress-text">${data.packaging.completionPercentage}% ${t.completed}</div>
              </div>
              <div class="status-card">
                <div class="info-label">${t.completedChecks}</div>
                <div class="info-value">${data.packaging.completedChecks}/${data.packaging.totalChecks}</div>
              </div>
              ${data.packaging.readinessDate ? `
                <div class="status-card">
                  <div class="info-label">${t.readinessDate}</div>
                  <div class="info-value">${formatDate(data.packaging.readinessDate)}</div>
                </div>
              ` : ''}
            </div>
          </div>
        </div>

        <!-- Packaging Checklist -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.packagingChecklist}</h2>
          </div>
          <div class="section-content">
            <table class="checklist-table">
              <thead>
                <tr>
                  <th>${t.items}</th>
                  <th>${t.status}</th>
                  <th>${t.checkedBy}</th>
                  <th>${t.checkedAt}</th>
                  <th>${t.notes}</th>
                </tr>
              </thead>
              <tbody>
                ${data.checklist.map(category => `
                  <tr class="checklist-category">
                    <td colspan="5"><strong>${category.category}</strong></td>
                  </tr>
                  ${category.items.map(item => `
                    <tr>
                      <td class="checklist-item">${item.name}</td>
                      <td class="status-${item.status}">
                        ${item.status === 'completed' ? t.completed :
                          item.status === 'pending' ? t.pending : t.fail}
                      </td>
                      <td>${item.checkedBy || '-'}</td>
                      <td>${item.checkedAt ? formatDateTime(item.checkedAt) : '-'}</td>
                      <td>${item.notes || '-'}</td>
                    </tr>
                  `).join('')}
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Packaging Photos -->
        ${data.packagingPhotos.length > 0 ? `
          <div class="section">
            <div class="section-header">
              <h2 class="section-title">${t.packagingPhotos}</h2>
            </div>
            <div class="section-content">
              <div class="photos-grid">
                ${data.packagingPhotos.map(photo => `
                  <div class="photo-item">
                    <div class="photo-placeholder">[${t.photos}]</div>
                    <div class="photo-caption">
                      <strong>${photo.category}</strong><br>
                      ${photo.caption}
                      ${photo.takenAt ? `<br><small>${formatDateTime(photo.takenAt)}</small>` : ''}
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>
        ` : ''}

        <!-- Shipping Labels -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.shippingLabels}</h2>
          </div>
          <div class="section-content">
            <div class="labels-grid">
              ${data.shippingLabels.map(label => `
                <div class="label-item">
                  <div class="label-type">${label.type.replace(/_/g, ' ')}</div>
                  <div class="label-status label-${label.status}">
                    ${label.status === 'approved' ? t.approved :
                      label.status === 'pending' ? t.pending : t.rejected}
                  </div>
                  ${label.notes ? `<div style="margin-top: 8px; font-size: 12px; color: #6b7280;">${label.notes}</div>` : ''}
                </div>
              `).join('')}
            </div>
          </div>
        </div>

        <!-- Quality Checks -->
        <div class="section">
          <div class="section-header">
            <h2 class="section-title">${t.qualityChecks}</h2>
          </div>
          <div class="section-content">
            <div class="quality-checks">
              ${data.qualityChecks.map(check => `
                <div class="quality-check">
                  <div>
                    <strong>${check.checkType}</strong>
                    ${check.details ? `<br><small>${check.details}</small>` : ''}
                    ${check.inspector ? `<br><small>${t.inspector}: ${check.inspector}</small>` : ''}
                  </div>
                  <div class="check-result result-${check.result}">
                    ${check.result === 'pass' ? t.pass :
                      check.result === 'conditional' ? t.conditional : t.fail}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>

        <!-- Final Approval -->
        <div class="final-approval">
          <div class="approval-badge approval-${data.finalApproval}">
            ${data.finalApproval === 'approved' ? t.approved :
              data.finalApproval === 'conditional' ? t.conditionalApproval : t.rejected}
          </div>
        </div>

        <!-- Shipment Readiness -->
        ${data.shipmentReadiness.estimatedShipDate || data.shipmentReadiness.actualShipDate ? `
          <div class="section">
            <div class="section-header">
              <h2 class="section-title">${t.shipmentReadiness}</h2>
            </div>
            <div class="section-content">
              <div class="shipment-info">
                <div class="shipment-title">${t.shipmentReadiness}</div>
                <div class="shipment-details">
                  ${data.shipmentReadiness.estimatedShipDate ? `
                    <div class="info-item">
                      <div class="info-label">${t.estimatedShipDate}</div>
                      <div class="info-value">${formatDate(data.shipmentReadiness.estimatedShipDate)}</div>
                    </div>
                  ` : ''}
                  ${data.shipmentReadiness.actualShipDate ? `
                    <div class="info-item">
                      <div class="info-label">${t.shipDate}</div>
                      <div class="info-value">${formatDate(data.shipmentReadiness.actualShipDate)}</div>
                    </div>
                  ` : ''}
                  ${data.shipmentReadiness.carrier ? `
                    <div class="info-item">
                      <div class="info-label">${t.carrier}</div>
                      <div class="info-value">${data.shipmentReadiness.carrier}</div>
                    </div>
                  ` : ''}
                  ${data.shipmentReadiness.trackingNumber ? `
                    <div class="info-item">
                      <div class="info-label">${t.trackingNumber}</div>
                      <div class="info-value">${data.shipmentReadiness.trackingNumber}</div>
                    </div>
                  ` : ''}
                </div>
              </div>
            </div>
          </div>
        ` : ''}

        <!-- Comments -->
        ${data.comments ? `
          <div class="section">
            <div class="section-header">
              <h2 class="section-title">${t.comments}</h2>
            </div>
            <div class="section-content">
              <div class="comments-box">
                ${data.comments}
              </div>
            </div>
          </div>
        ` : ''}

      </body>
      </html>
    `;
  }

  private async generateDppSummaryReport(report: Report): Promise<string> {
    const params = report.parameters as DppSummaryParams;

    // Get data for the report
    const data: DppSummaryReportData = await this.getDppSummaryReportData(
      report.clientId,
      params
    );

    // Render HTML template
    const htmlContent = await this.renderDppSummaryReportTemplate(data, report.language || ReportLanguage.EN);

    // Generate PDF
    const key = await this.generatePDF(htmlContent, `dpp-summary-${report.id}.pdf`, report.clientId, { format: 'A4' });
    return key;
  }

  private async getDppSummaryReportData(
    clientId: string,
    params: DppSummaryParams
  ): Promise<DppSummaryReportData> {
    // In a real implementation, this would fetch actual DPP data from the database
    // For now, returning comprehensive sample data

    return {
      dpp: {
        id: params.dppId || 'dpp-001',
        lotId: params.lotId,
        purchaseOrderNumber: params.purchaseOrderNumber,
        status: 'published',
        version: '1.2.0',
        publishedAt: '2024-01-15T10:00:00Z',
        expiresAt: '2029-01-15T10:00:00Z'
      },
      product: {
        name: 'Premium Cotton T-Shirt',
        styleRef: 'CT-2024-001',
        description: 'Classic fit cotton t-shirt made from 100% organic cotton with GOTS certification',
        category: 'Apparel',
        season: 'Spring/Summer 2024',
        composition: [
          {
            material: 'Organic Cotton',
            percentage: 95,
            origin: 'India',
            certifications: ['GOTS', 'OCS']
          },
          {
            material: 'Elastane',
            percentage: 5,
            origin: 'Germany',
            certifications: ['OEKO-TEX']
          }
        ],
        care: {
          washingTemp: 30,
          dryingMethod: 'Air dry',
          ironingTemp: 'Medium',
          specialCare: ['Do not bleach', 'Wash with similar colors']
        }
      },
      sustainability: {
        carbonFootprint: {
          total: 3.2,
          unit: 'kg CO2e',
          breakdown: [
            { stage: 'Raw Materials', amount: 1.8, percentage: 56.3 },
            { stage: 'Manufacturing', amount: 0.9, percentage: 28.1 },
            { stage: 'Transportation', amount: 0.3, percentage: 9.4 },
            { stage: 'Packaging', amount: 0.2, percentage: 6.3 }
          ]
        },
        waterUsage: {
          total: 2700,
          unit: 'liters',
          breakdown: [
            { stage: 'Cotton Growing', amount: 2000, percentage: 74.1 },
            { stage: 'Processing', amount: 500, percentage: 18.5 },
            { stage: 'Dyeing', amount: 150, percentage: 5.6 },
            { stage: 'Finishing', amount: 50, percentage: 1.9 }
          ]
        },
        recyclability: {
          percentage: 85,
          methods: ['Mechanical recycling', 'Chemical recycling'],
          instructions: 'Remove labels and wash before recycling. Can be processed through textile recycling programs.'
        },
        certifications: [
          {
            name: 'Global Organic Textile Standard (GOTS)',
            issuer: 'GOTS International',
            validFrom: '2023-01-01',
            validTo: '2026-01-01',
            certificateNumber: 'GOTS-2023-001'
          },
          {
            name: 'OEKO-TEX Standard 100',
            issuer: 'OEKO-TEX International',
            validFrom: '2023-06-01',
            validTo: '2024-06-01',
            certificateNumber: 'OTX-2023-456'
          }
        ]
      },
      supplyChain: {
        suppliers: [
          {
            name: 'Green Cotton Mills Ltd',
            role: 'Primary Manufacturer',
            location: 'Tamil Nadu, India',
            tier: 1,
            certifications: ['GOTS', 'SA8000', 'ISO 14001'],
            sustainabilityScore: 92
          },
          {
            name: 'Organic Farm Cooperative',
            role: 'Cotton Supplier',
            location: 'Gujarat, India',
            tier: 2,
            certifications: ['GOTS', 'Fair Trade'],
            sustainabilityScore: 88
          },
          {
            name: 'EcoThread Spinners',
            role: 'Yarn Manufacturer',
            location: 'Karnataka, India',
            tier: 2,
            certifications: ['GOTS', 'GRS'],
            sustainabilityScore: 85
          }
        ],
        totalSuppliers: 3,
        geographicSpread: [
          { country: 'India', percentage: 100 }
        ]
      },
      compliance: {
        regulations: [
          {
            name: 'EU Textile Regulation',
            region: 'Europe',
            status: 'compliant',
            validatedAt: '2024-01-10T09:00:00Z'
          },
          {
            name: 'CPSIA Lead Content',
            region: 'United States',
            status: 'compliant',
            validatedAt: '2024-01-10T09:00:00Z'
          },
          {
            name: 'Chinese National Standard GB 18401',
            region: 'China',
            status: 'compliant',
            validatedAt: '2024-01-10T09:00:00Z'
          }
        ],
        testResults: [
          {
            testType: 'Chemical Safety',
            standard: 'OEKO-TEX Standard 100',
            result: 'pass',
            testedAt: '2023-12-15T14:00:00Z',
            laboratory: 'OEKO-TEX Eco Passport Lab',
            certificateNumber: 'OTX-TEST-2023-789'
          },
          {
            testType: 'Colorfastness',
            standard: 'ISO 105-C06',
            result: 'pass',
            testedAt: '2023-12-20T10:00:00Z',
            laboratory: 'Quality Assurance Labs India',
            certificateNumber: 'QAL-CF-2023-456'
          }
        ]
      },
      traceability: {
        batchNumber: 'CT001-240115',
        productionDate: '2024-01-15',
        factoryLocation: 'Green Cotton Mills, Tamil Nadu, India',
        rawMaterialOrigins: [
          {
            material: 'Organic Cotton',
            origin: 'Gujarat, India',
            supplier: 'Organic Farm Cooperative',
            harvestDate: '2023-11-15'
          }
        ],
        productionSteps: [
          {
            step: 'Ginning',
            location: 'Gujarat, India',
            supplier: 'Organic Farm Cooperative',
            completedAt: '2023-11-20',
            co2Impact: 0.1
          },
          {
            step: 'Spinning',
            location: 'Karnataka, India',
            supplier: 'EcoThread Spinners',
            completedAt: '2023-12-01',
            co2Impact: 0.3
          },
          {
            step: 'Knitting & Dyeing',
            location: 'Tamil Nadu, India',
            supplier: 'Green Cotton Mills Ltd',
            completedAt: '2024-01-10',
            co2Impact: 0.6
          },
          {
            step: 'Finishing & Packaging',
            location: 'Tamil Nadu, India',
            supplier: 'Green Cotton Mills Ltd',
            completedAt: '2024-01-15',
            co2Impact: 0.2
          }
        ]
      },
      circularity: {
        designForCircularity: {
          score: 75,
          maxScore: 100,
          factors: [
            { factor: 'Material Selection', score: 18, maxScore: 20, description: 'High-quality organic materials selected for durability' },
            { factor: 'Durability', score: 17, maxScore: 20, description: 'Reinforced seams and quality construction for extended lifespan' },
            { factor: 'Repairability', score: 14, maxScore: 20, description: 'Standard construction allows for basic repairs' },
            { factor: 'Recyclability', score: 16, maxScore: 20, description: 'Natural fibers easily recyclable through established programs' },
            { factor: 'Disassembly', score: 10, maxScore: 20, description: 'Limited disassembly due to blended materials in trim' }
          ]
        },
        repairability: {
          score: 70,
          instructions: [
            'Small holes can be darned using matching cotton thread',
            'Loose seams can be re-stitched by hand or machine',
            'Replace buttons if they become loose or damaged'
          ],
          spareParts: ['Replacement buttons available from manufacturer']
        },
        endOfLife: {
          options: [
            {
              method: 'Textile Recycling',
              description: 'Drop off at textile recycling centers or return to retailer',
              environmentalImpact: 'Reduces waste and conserves resources'
            },
            {
              method: 'Composting (cotton only)',
              description: 'Remove synthetic components, cotton portion is biodegradable',
              environmentalImpact: 'Returns nutrients to soil, but requires proper separation'
            },
            {
              method: 'Upcycling',
              description: 'Repurpose into rags, quilting material, or other textile products',
              environmentalImpact: 'Extends product life and reduces waste'
            }
          ],
          recommendations: [
            'Choose textile recycling as the preferred end-of-life option',
            'Clean garment before disposal',
            'Remove any non-textile components if possible'
          ]
        }
      },
      accessibilityInfo: {
        qrCode: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        nfcEnabled: true,
        digitalTwinUrl: 'https://dpp.example.com/ct-2024-001',
        mobileAppDeeplink: 'sustainableapp://product/ct-2024-001',
        supportedLanguages: ['en', 'es', 'fr', 'de', 'pt']
      }
    };
  }

  private async renderDppSummaryReportTemplate(
    data: DppSummaryReportData,
    language: ReportLanguage
  ): Promise<string> {
    const t = this.getTranslations(language);

    const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString();
    const formatDateTime = (dateStr: string) => new Date(dateStr).toLocaleString();

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>${t.dppSummaryReport}</title>
        <style>
          body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            color: #333;
            line-height: 1.6;
          }
          .header {
            background: linear-gradient(135deg, #2ecc71, #27ae60);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(46, 204, 113, 0.3);
          }
          .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
          }
          .header .subtitle {
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
          }
          .dpp-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 5px solid #2ecc71;
          }
          .section {
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            border: 1px solid #e9ecef;
          }
          .section-title {
            color: #2ecc71;
            margin-bottom: 20px;
            font-size: 1.5em;
            font-weight: 600;
            border-bottom: 2px solid #2ecc71;
            padding-bottom: 10px;
          }
          .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
          }
          .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #e9ecef;
          }
          .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #2ecc71;
            margin-bottom: 5px;
          }
          .metric-label {
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
          }
          .composition-table, .supplier-table, .compliance-table, .test-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
          }
          .composition-table th, .supplier-table th, .compliance-table th, .test-table th,
          .composition-table td, .supplier-table td, .compliance-table td, .test-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
          }
          .composition-table th, .supplier-table th, .compliance-table th, .test-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
          }
          .breakdown-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
          }
          .breakdown-item:last-child {
            border-bottom: none;
          }
          .breakdown-bar {
            height: 8px;
            background: #2ecc71;
            border-radius: 4px;
            margin-top: 5px;
          }
          .status-compliant {
            color: #27ae60;
            font-weight: bold;
          }
          .status-pending {
            color: #f39c12;
            font-weight: bold;
          }
          .status-non-compliant {
            color: #e74c3c;
            font-weight: bold;
          }
          .result-pass {
            color: #27ae60;
            font-weight: bold;
          }
          .result-fail {
            color: #e74c3c;
            font-weight: bold;
          }
          .progress-circle {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: conic-gradient(#2ecc71 0deg ${data.circularity.designForCircularity.score * 3.6}deg, #e9ecef 0deg);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 15px;
            position: relative;
          }
          .progress-circle::before {
            content: '${data.circularity.designForCircularity.score}%';
            width: 60px;
            height: 60px;
            background: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: #2ecc71;
          }
          .traceability-timeline {
            position: relative;
            padding-left: 30px;
          }
          .traceability-timeline::before {
            content: '';
            position: absolute;
            left: 15px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #2ecc71;
          }
          .timeline-item {
            position: relative;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #2ecc71;
          }
          .timeline-item::before {
            content: '';
            position: absolute;
            left: -37px;
            top: 20px;
            width: 12px;
            height: 12px;
            background: #2ecc71;
            border-radius: 50%;
            border: 3px solid white;
          }
          .care-instructions {
            background: #e8f5e8;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
          }
          .care-instructions ul {
            margin: 0;
            padding-left: 20px;
          }
          .certifications-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
          }
          .certification-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #2ecc71;
          }
          .qr-code {
            text-align: center;
            margin: 20px 0;
          }
          .qr-code img {
            width: 120px;
            height: 120px;
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 8px;
          }
          .accessibility-features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
          }
          .accessibility-card {
            background: #f8f9fa;
            padding: 15px;
            text-align: center;
            border-radius: 8px;
            border: 1px solid #e9ecef;
          }
          .accessibility-card.enabled {
            background: #e8f5e8;
            border-color: #2ecc71;
          }
          @media print {
            .section {
              break-inside: avoid;
              page-break-inside: avoid;
            }
          }
        </style>
      </head>
      <body>

        <!-- Header -->
        <div class="header">
          <h1>${t.dppSummaryReport}</h1>
          <div class="subtitle">${t.digitalProductPassport}</div>
        </div>

        <!-- DPP Information -->
        <div class="dpp-info">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
            <div>
              <strong>${t.dppId}:</strong> ${data.dpp.id}<br>
              <strong>${t.version}:</strong> ${data.dpp.version}<br>
              <strong>${t.status}:</strong> <span style="color: #27ae60; font-weight: bold;">${data.dpp.status.toUpperCase()}</span>
            </div>
            <div>
              ${data.dpp.publishedAt ? `<strong>${t.publishedAt}:</strong> ${formatDateTime(data.dpp.publishedAt)}<br>` : ''}
              ${data.dpp.expiresAt ? `<strong>${t.expiresAt}:</strong> ${formatDate(data.dpp.expiresAt)}<br>` : ''}
              ${data.dpp.lotId ? `<strong>${t.lotId}:</strong> ${data.dpp.lotId}` : ''}
            </div>
          </div>
        </div>

        <!-- Product Information -->
        <div class="section">
          <h2 class="section-title">${t.productInformation}</h2>
          <div class="two-column">
            <div>
              <p><strong>${t.productName}:</strong> ${data.product.name}</p>
              <p><strong>${t.styleRef}:</strong> ${data.product.styleRef}</p>
              <p><strong>${t.category}:</strong> ${data.product.category}</p>
              <p><strong>${t.season}:</strong> ${data.product.season}</p>
              <p><strong>${t.description}:</strong> ${data.product.description}</p>
            </div>
            <div>
              <h4>${t.composition}:</h4>
              <table class="composition-table">
                <thead>
                  <tr>
                    <th>${t.material}</th>
                    <th>${t.percentage}</th>
                    <th>${t.origin}</th>
                  </tr>
                </thead>
                <tbody>
                  ${data.product.composition.map(comp => `
                    <tr>
                      <td>${comp.material}</td>
                      <td>${comp.percentage}%</td>
                      <td>${comp.origin || '-'}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>

              <div class="care-instructions">
                <h4>${t.careInstructions}:</h4>
                <ul>
                  <li>${t.washingTemp}: ${data.product.care.washingTemp}°C</li>
                  <li>${t.drying}: ${data.product.care.dryingMethod}</li>
                  <li>${t.ironing}: ${data.product.care.ironingTemp}</li>
                  ${data.product.care.specialCare?.map(instruction => `<li>${instruction}</li>`).join('') || ''}
                </ul>
              </div>
            </div>
          </div>
        </div>

        <!-- Sustainability Metrics -->
        <div class="section">
          <h2 class="section-title">${t.sustainabilityMetrics}</h2>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; margin-bottom: 30px;">
            <div class="metric-card">
              <div class="metric-value">${data.sustainability.carbonFootprint.total} ${data.sustainability.carbonFootprint.unit}</div>
              <div class="metric-label">${t.carbonFootprint}</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">${data.sustainability.waterUsage.total} ${data.sustainability.waterUsage.unit}</div>
              <div class="metric-label">${t.waterUsage}</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">${data.sustainability.recyclability.percentage}%</div>
              <div class="metric-label">${t.recyclability}</div>
            </div>
          </div>

          <div class="two-column">
            <div>
              <h4>${t.carbonFootprintBreakdown}:</h4>
              ${data.sustainability.carbonFootprint.breakdown.map(item => `
                <div class="breakdown-item">
                  <span>${item.stage}: ${item.amount} ${data.sustainability.carbonFootprint.unit}</span>
                  <span>${item.percentage}%</span>
                </div>
                <div class="breakdown-bar" style="width: ${item.percentage}%"></div>
              `).join('')}
            </div>
            <div>
              <h4>${t.waterUsageBreakdown}:</h4>
              ${data.sustainability.waterUsage.breakdown.map(item => `
                <div class="breakdown-item">
                  <span>${item.stage}: ${item.amount} ${data.sustainability.waterUsage.unit}</span>
                  <span>${item.percentage}%</span>
                </div>
                <div class="breakdown-bar" style="width: ${item.percentage}%"></div>
              `).join('')}
            </div>
          </div>
        </div>

        <!-- Supply Chain -->
        <div class="section">
          <h2 class="section-title">${t.supplyChain}</h2>
          <table class="supplier-table">
            <thead>
              <tr>
                <th>${t.supplier}</th>
                <th>${t.role}</th>
                <th>${t.location}</th>
                <th>${t.tier}</th>
                <th>${t.sustainabilityScore}</th>
                <th>${t.certifications}</th>
              </tr>
            </thead>
            <tbody>
              ${data.supplyChain.suppliers.map(supplier => `
                <tr>
                  <td>${supplier.name}</td>
                  <td>${supplier.role}</td>
                  <td>${supplier.location}</td>
                  <td>${t.tier} ${supplier.tier}</td>
                  <td><strong style="color: #2ecc71;">${supplier.sustainabilityScore}/100</strong></td>
                  <td>${supplier.certifications.join(', ')}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

        <!-- Compliance -->
        <div class="section">
          <h2 class="section-title">${t.compliance}</h2>

          <h4>${t.regulations}:</h4>
          <table class="compliance-table">
            <thead>
              <tr>
                <th>${t.regulation}</th>
                <th>${t.region}</th>
                <th>${t.status}</th>
                <th>${t.validatedAt}</th>
              </tr>
            </thead>
            <tbody>
              ${data.compliance.regulations.map(reg => `
                <tr>
                  <td>${reg.name}</td>
                  <td>${reg.region}</td>
                  <td><span class="status-${reg.status.replace('_', '-')}">${reg.status.toUpperCase()}</span></td>
                  <td>${reg.validatedAt ? formatDateTime(reg.validatedAt) : '-'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>

          <h4 style="margin-top: 30px;">${t.testResults}:</h4>
          <table class="test-table">
            <thead>
              <tr>
                <th>${t.testType}</th>
                <th>${t.standard}</th>
                <th>${t.result}</th>
                <th>${t.laboratory}</th>
                <th>${t.testedAt}</th>
              </tr>
            </thead>
            <tbody>
              ${data.compliance.testResults.map(test => `
                <tr>
                  <td>${test.testType}</td>
                  <td>${test.standard}</td>
                  <td><span class="result-${test.result}">${test.result.toUpperCase()}</span></td>
                  <td>${test.laboratory}</td>
                  <td>${formatDateTime(test.testedAt)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

        <!-- Traceability -->
        <div class="section">
          <h2 class="section-title">${t.traceability}</h2>

          <div style="margin-bottom: 30px;">
            <p><strong>${t.batchNumber}:</strong> ${data.traceability.batchNumber}</p>
            <p><strong>${t.productionDate}:</strong> ${formatDate(data.traceability.productionDate)}</p>
            <p><strong>${t.factoryLocation}:</strong> ${data.traceability.factoryLocation}</p>
          </div>

          <h4>${t.productionTimeline}:</h4>
          <div class="traceability-timeline">
            ${data.traceability.productionSteps.map(step => `
              <div class="timeline-item">
                <strong>${step.step}</strong><br>
                <small>${step.location} • ${step.supplier}</small><br>
                <small>${t.completed}: ${formatDate(step.completedAt)} • CO₂: ${step.co2Impact} kg</small>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Circularity -->
        <div class="section">
          <h2 class="section-title">${t.circularity}</h2>

          <div class="two-column">
            <div>
              <h4>${t.designForCircularity}:</h4>
              <div style="text-align: center; margin-bottom: 20px;">
                <div class="progress-circle"></div>
                <div style="font-size: 0.9em; color: #666;">${data.circularity.designForCircularity.score}/${data.circularity.designForCircularity.maxScore} ${t.points}</div>
              </div>

              ${data.circularity.designForCircularity.factors.map(factor => `
                <div style="margin-bottom: 15px;">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <strong>${factor.factor}</strong>
                    <span>${factor.score}/${factor.maxScore}</span>
                  </div>
                  <div style="background: #e9ecef; height: 6px; border-radius: 3px;">
                    <div style="background: #2ecc71; height: 100%; width: ${(factor.score / factor.maxScore) * 100}%; border-radius: 3px;"></div>
                  </div>
                  <small style="color: #666;">${factor.description}</small>
                </div>
              `).join('')}
            </div>

            <div>
              <h4>${t.endOfLifeOptions}:</h4>
              ${data.circularity.endOfLife.options.map(option => `
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                  <strong>${option.method}</strong><br>
                  <small>${option.description}</small><br>
                  <small style="color: #2ecc71;"><strong>${t.impact}:</strong> ${option.environmentalImpact}</small>
                </div>
              `).join('')}

              <h4>${t.recommendations}:</h4>
              <ul>
                ${data.circularity.endOfLife.recommendations.map(rec => `<li>${rec}</li>`).join('')}
              </ul>
            </div>
          </div>
        </div>

        <!-- Certifications -->
        <div class="section">
          <h2 class="section-title">${t.certifications}</h2>
          <div class="certifications-grid">
            ${data.sustainability.certifications.map(cert => `
              <div class="certification-card">
                <strong>${cert.name}</strong><br>
                <small>${t.issuer}: ${cert.issuer}</small><br>
                <small>${t.valid}: ${formatDate(cert.validFrom)} - ${formatDate(cert.validTo)}</small><br>
                <small>${t.certificateNumber}: ${cert.certificateNumber}</small>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Accessibility & Access -->
        <div class="section">
          <h2 class="section-title">${t.digitalAccess}</h2>

          <div class="two-column">
            <div>
              <div class="qr-code">
                <h4>${t.scanForDetails}:</h4>
                <img src="${data.accessibilityInfo.qrCode}" alt="QR Code">
                <p><small>${t.scanWithPhone}</small></p>
              </div>
            </div>

            <div>
              <h4>${t.accessibilityFeatures}:</h4>
              <div class="accessibility-features">
                <div class="accessibility-card ${data.accessibilityInfo.nfcEnabled ? 'enabled' : ''}">
                  <strong>NFC</strong><br>
                  <small>${data.accessibilityInfo.nfcEnabled ? t.enabled : t.disabled}</small>
                </div>
                <div class="accessibility-card ${data.accessibilityInfo.digitalTwinUrl ? 'enabled' : ''}">
                  <strong>${t.digitalTwin}</strong><br>
                  <small>${data.accessibilityInfo.digitalTwinUrl ? t.available : t.notAvailable}</small>
                </div>
                <div class="accessibility-card ${data.accessibilityInfo.mobileAppDeeplink ? 'enabled' : ''}">
                  <strong>${t.mobileApp}</strong><br>
                  <small>${data.accessibilityInfo.mobileAppDeeplink ? t.available : t.notAvailable}</small>
                </div>
              </div>

              <h4>${t.supportedLanguages}:</h4>
              <p>${data.accessibilityInfo.supportedLanguages.join(', ')}</p>
            </div>
          </div>
        </div>

      </body>
      </html>
    `;
  }

  async listReports(clientId: string, type?: ReportType): Promise<Report[]> {
    const query = this.reportRepository.createQueryBuilder('report')
      .where('report.clientId = :clientId', { clientId })
      .orderBy('report.createdAt', 'DESC');

    if (type) {
      query.andWhere('report.type = :type', { type });
    }

    return await query.getMany();
  }

  async getReport(id: string, clientId: string): Promise<Report> {
    const report = await this.reportRepository.findOne({
      where: { id, clientId }
    });

    if (!report) {
      throw new NotFoundException('Report not found');
    }

    return report;
  }

  async getReportFile(id: string, clientId: string): Promise<Buffer> {
    const report = await this.getReport(id, clientId);

    if (!report.filePath) {
      throw new NotFoundException('Report file not found');
    }

    try {
      const fileBuffer = await this.storageService.getFileBuffer(report.filePath, 'reports');
      return fileBuffer;
    } catch (error) {
      this.logger.error(`Failed to read report file: ${error}`);
      throw new NotFoundException('Report file not found or inaccessible');
    }
  }

}
