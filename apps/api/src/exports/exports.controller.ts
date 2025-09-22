import { Controller, Post, Body, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { ExportsService } from './exports.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { TenantId } from '../common/decorators';
import { ExportQuery, ExportQuerySchema } from '@qa-dashboard/shared';
import { ZodValidationPipe } from '../common/zod-validation.pipe';

@ApiTags('exports')
@Controller('exports')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class ExportsController {
  constructor(private exportsService: ExportsService) {}

  @Post('pdf')
  @ApiOperation({ summary: 'Generate PDF report' })
  async generatePDF(
    @TenantId() tenantId: string,
    @Body(new ZodValidationPipe(ExportQuerySchema)) query: ExportQuery,
  ): Promise<{ downloadUrl: string }> {
    const downloadUrl = await this.exportsService.generatePDF(
      tenantId,
      query.batchId,
      query.range,
    );
    
    return { downloadUrl };
  }

  @Post('csv')
  @ApiOperation({ summary: 'Generate CSV export' })
  async generateCSV(
    @TenantId() tenantId: string,
    @Body(new ZodValidationPipe(ExportQuerySchema)) query: ExportQuery,
  ): Promise<{ downloadUrl: string }> {
    const downloadUrl = await this.exportsService.generateCSV(tenantId, query.range);
    return { downloadUrl };
  }
}