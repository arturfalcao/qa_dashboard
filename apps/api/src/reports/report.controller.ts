import {
  Controller,
  Post,
  Get,
  Param,
  Body,
  Query,
  Res,
  HttpCode,
  HttpStatus,
  ForbiddenException,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiQuery, ApiProduces } from '@nestjs/swagger';
import { Response } from 'express';
import { ReportService } from './report.service';
import { ClientId, CurrentUser } from '../common/decorators';
import { ReportType, ReportLanguage, UserRole } from '@qa-dashboard/shared';
import {
  ReportGenerationRequest,
  ExecutiveQualitySummaryParams,
  LotInspectionReportParams,
  MeasurementComplianceSheetParams,
  PackagingReadinessReportParams,
  SupplierPerformanceSnapshotParams,
  CapaReportParams,
  InlineQcCheckpointsParams,
  DppSummaryParams,
} from './report-types';

@ApiTags('reports')
@Controller('reports')
export class ReportController {
  constructor(private readonly reportService: ReportService) {}

  private ensureReportPermissions(user?: { roles?: UserRole[] }) {
    const roles = user?.roles || [];
    const allowed = [UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.CLEVEL];
    if (roles.length > 0 && !roles.some((role) => allowed.includes(role))) {
      throw new ForbiddenException('User lacks permissions to generate reports');
    }
  }

  @Post('executive-summary')
  @ApiOperation({ summary: 'Generate Executive Quality Summary report' })
  @HttpCode(HttpStatus.ACCEPTED)
  async generateExecutiveSummary(
    @ClientId() clientId: string,
    @Body() params: ExecutiveQualitySummaryParams,
    @Query('language') language?: ReportLanguage,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);

    const request: ReportGenerationRequest = {
      type: ReportType.EXECUTIVE_QUALITY_SUMMARY,
      clientId,
      userId: user?.userId,
      language: language || ReportLanguage.EN,
      parameters: params,
    };

    return await this.reportService.generateReport(request);
  }

  @Post('lot-inspection/:lotId')
  @ApiOperation({ summary: 'Generate Lot Inspection Report' })
  @HttpCode(HttpStatus.ACCEPTED)
  async generateLotInspectionReport(
    @ClientId() clientId: string,
    @Param('lotId') lotId: string,
    @Body() params: Omit<LotInspectionReportParams, 'lotId'>,
    @Query('language') language?: ReportLanguage,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);

    const request: ReportGenerationRequest = {
      type: ReportType.LOT_INSPECTION_REPORT,
      clientId,
      userId: user?.userId,
      language: language || ReportLanguage.EN,
      parameters: { ...params, lotId },
    };

    return await this.reportService.generateReport(request);
  }

  @Post('measurement-compliance/:lotId')
  @ApiOperation({ summary: 'Generate Measurement Compliance Sheet' })
  @HttpCode(HttpStatus.ACCEPTED)
  async generateMeasurementComplianceSheet(
    @ClientId() clientId: string,
    @Param('lotId') lotId: string,
    @Body() params: Omit<MeasurementComplianceSheetParams, 'lotId'>,
    @Query('language') language?: ReportLanguage,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);

    const request: ReportGenerationRequest = {
      type: ReportType.MEASUREMENT_COMPLIANCE_SHEET,
      clientId,
      userId: user?.userId,
      language: language || ReportLanguage.EN,
      parameters: { ...params, lotId },
    };

    return await this.reportService.generateReport(request);
  }

  @Post('packaging-readiness/:lotId')
  @ApiOperation({ summary: 'Generate Packaging & Readiness Report' })
  @HttpCode(HttpStatus.ACCEPTED)
  async generatePackagingReadinessReport(
    @ClientId() clientId: string,
    @Param('lotId') lotId: string,
    @Body() params: Omit<PackagingReadinessReportParams, 'lotId'>,
    @Query('language') language?: ReportLanguage,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);

    const request: ReportGenerationRequest = {
      type: ReportType.PACKAGING_READINESS_REPORT,
      clientId,
      userId: user?.userId,
      language: language || ReportLanguage.EN,
      parameters: { ...params, lotId },
    };

    return await this.reportService.generateReport(request);
  }

  @Post('supplier-performance')
  @ApiOperation({ summary: 'Generate Supplier Performance Snapshot' })
  @HttpCode(HttpStatus.ACCEPTED)
  async generateSupplierPerformanceSnapshot(
    @ClientId() clientId: string,
    @Body() params: SupplierPerformanceSnapshotParams,
    @Query('language') language?: ReportLanguage,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);

    const request: ReportGenerationRequest = {
      type: ReportType.SUPPLIER_PERFORMANCE_SNAPSHOT,
      clientId,
      userId: user?.userId,
      language: language || ReportLanguage.EN,
      parameters: params,
    };

    return await this.reportService.generateReport(request);
  }

  @Post('capa/:capaId')
  @ApiOperation({ summary: 'Generate CAPA Report' })
  @HttpCode(HttpStatus.ACCEPTED)
  async generateCapaReport(
    @ClientId() clientId: string,
    @Param('capaId') capaId: string,
    @Body() params: Omit<CapaReportParams, 'capaId'>,
    @Query('language') language?: ReportLanguage,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);

    const request: ReportGenerationRequest = {
      type: ReportType.CAPA_REPORT,
      clientId,
      userId: user?.userId,
      language: language || ReportLanguage.EN,
      parameters: { ...params, capaId },
    };

    return await this.reportService.generateReport(request);
  }

  @Post('inline-qc/:lotId')
  @ApiOperation({ summary: 'Generate Inline QC Checkpoints report' })
  @HttpCode(HttpStatus.ACCEPTED)
  async generateInlineQcCheckpoints(
    @ClientId() clientId: string,
    @Param('lotId') lotId: string,
    @Body() params: Omit<InlineQcCheckpointsParams, 'lotId'>,
    @Query('language') language?: ReportLanguage,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);

    const request: ReportGenerationRequest = {
      type: ReportType.INLINE_QC_CHECKPOINTS,
      clientId,
      userId: user?.userId,
      language: language || ReportLanguage.EN,
      parameters: { ...params, lotId },
    };

    return await this.reportService.generateReport(request);
  }

  @Post('dpp-summary')
  @ApiOperation({ summary: 'Generate DPP Summary report' })
  @HttpCode(HttpStatus.ACCEPTED)
  async generateDppSummary(
    @ClientId() clientId: string,
    @Body() params: DppSummaryParams,
    @Query('language') language?: ReportLanguage,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);

    const request: ReportGenerationRequest = {
      type: ReportType.DPP_SUMMARY,
      clientId,
      userId: user?.userId,
      language: language || ReportLanguage.EN,
      parameters: params,
    };

    return await this.reportService.generateReport(request);
  }

  @Get()
  @ApiOperation({ summary: 'List reports for client' })
  @ApiQuery({ name: 'type', enum: ReportType, required: false })
  async listReports(
    @ClientId() clientId: string,
    @Query('type') type?: ReportType,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);
    return await this.reportService.listReports(clientId, type);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get report details' })
  async getReport(
    @ClientId() clientId: string,
    @Param('id') id: string,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);
    return await this.reportService.getReport(id, clientId);
  }

  @Get(':id/download')
  @ApiOperation({ summary: 'Download report PDF' })
  @ApiProduces('application/pdf')
  async downloadReport(
    @ClientId() clientId: string,
    @Param('id') id: string,
    @Res() res: Response,
    @CurrentUser() user?: { roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);

    const report = await this.reportService.getReport(id, clientId);
    const fileBuffer = await this.reportService.getReportFile(id, clientId);

    res.set({
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${report.fileName}"`,
      'Content-Length': fileBuffer.length,
    });

    res.send(fileBuffer);
  }

  // Generic report generation endpoint for flexibility
  @Post('generate')
  @ApiOperation({ summary: 'Generate report (generic endpoint)' })
  @HttpCode(HttpStatus.ACCEPTED)
  async generateReport(
    @ClientId() clientId: string,
    @Body() request: Omit<ReportGenerationRequest, 'clientId'>,
    @CurrentUser() user?: { userId?: string; roles?: UserRole[] },
  ) {
    this.ensureReportPermissions(user);

    const fullRequest: ReportGenerationRequest = {
      ...request,
      clientId,
      userId: user?.userId,
    };

    return await this.reportService.generateReport(fullRequest);
  }
}