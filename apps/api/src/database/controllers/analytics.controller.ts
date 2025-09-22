import { Controller, Get, Query, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth, ApiQuery } from '@nestjs/swagger';
import { AnalyticsService } from '../services/analytics.service';
import { JwtAuthGuard } from '../../auth/jwt-auth.guard';
import { TenantId, Public } from '../../common/decorators';
import { AnalyticsQuery, ThroughputQuery, AnalyticsQuerySchema, ThroughputQuerySchema } from '@qa-dashboard/shared';
import { ZodValidationPipe } from '../../common/zod-validation.pipe';

@ApiTags('analytics')
@Controller('analytics')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class AnalyticsController {
  constructor(private analyticsService: AnalyticsService) {}

  @Get('defect-rate')
  @Public()
  @ApiOperation({ summary: 'Get defect rate analytics' })
  @ApiQuery({ name: 'groupBy', required: false, enum: ['style', 'vendor'] })
  @ApiQuery({ name: 'range', required: false, enum: ['last_7d', 'last_30d'] })
  async getDefectRate(
    @TenantId() tenantId: string,
    @Query('groupBy') groupBy?: 'style' | 'vendor',
    @Query('range') range?: 'last_7d' | 'last_30d',
  ) {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    return this.analyticsService.getDefectRate(finalTenantId, range || 'last_7d', groupBy);
  }

  @Get('throughput')
  @Public()
  @ApiOperation({ summary: 'Get throughput analytics' })
  @ApiQuery({ name: 'bucket', required: false, enum: ['day', 'week'] })
  @ApiQuery({ name: 'range', required: false, enum: ['last_7d', 'last_30d'] })
  async getThroughput(
    @TenantId() tenantId: string,
    @Query('bucket') bucket?: 'day' | 'week',
    @Query('range') range?: 'last_7d' | 'last_30d',
  ) {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    return this.analyticsService.getThroughput(finalTenantId, bucket || 'day', range || 'last_7d');
  }

  @Get('defect-types')
  @Public()
  @ApiOperation({ summary: 'Get defect type breakdown' })
  @ApiQuery({ name: 'range', required: false, enum: ['last_7d', 'last_30d'] })
  async getDefectTypes(
    @TenantId() tenantId: string,
    @Query('range') range?: 'last_7d' | 'last_30d',
  ) {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    return this.analyticsService.getDefectTypes(finalTenantId, range || 'last_7d');
  }

  @Get('approval-time')
  @Public()
  @ApiOperation({ summary: 'Get approval time analytics' })
  @ApiQuery({ name: 'range', required: false, enum: ['last_7d', 'last_30d'] })
  async getApprovalTime(
    @TenantId() tenantId: string,
    @Query('range') range?: 'last_7d' | 'last_30d',
  ) {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    return this.analyticsService.getApprovalTime(finalTenantId, range || 'last_7d');
  }
}