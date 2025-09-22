import { Controller, Post, Body, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { ExportsService } from './exports.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { TenantId, Public } from '../common/decorators';
import { ExportQuery, ExportQuerySchema } from '@qa-dashboard/shared';
import { ZodValidationPipe } from '../common/zod-validation.pipe';

@ApiTags('exports')
@Controller('exports')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class ExportsController {
  constructor(private exportsService: ExportsService) {}

  @Post('pdf')
  @Public()
  @ApiOperation({ summary: 'Generate PDF report' })
  async generatePDF(
    @TenantId() tenantId: string,
    @Body(new ZodValidationPipe(ExportQuerySchema)) query: ExportQuery,
  ): Promise<{ downloadUrl: string }> {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    const downloadUrl = await this.exportsService.generatePDF(
      finalTenantId,
      query.batchId,
      query.range,
    );
    
    return { downloadUrl };
  }

  @Post('csv')
  @Public()
  @ApiOperation({ summary: 'Generate CSV export' })
  async generateCSV(
    @TenantId() tenantId: string,
    @Body(new ZodValidationPipe(ExportQuerySchema)) query: ExportQuery,
  ): Promise<{ downloadUrl: string }> {
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    const downloadUrl = await this.exportsService.generateCSV(finalTenantId, query.range);
    return { downloadUrl };
  }
}