import { Controller, Get, Query, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth, ApiQuery } from '@nestjs/swagger';
import { InspectionService } from '../services/inspection.service';
import { JwtAuthGuard } from '../../auth/jwt-auth.guard';
import { TenantId } from '../../common/decorators';

@ApiTags('inspections')
@Controller('inspections')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class InspectionController {
  constructor(private inspectionService: InspectionService) {}

  @Get()
  @ApiOperation({ summary: 'Get inspections for tenant' })
  @ApiQuery({ name: 'since', required: false, description: 'ISO date string' })
  @ApiQuery({ name: 'limit', required: false, type: Number, description: 'Limit results' })
  async getInspections(
    @TenantId() tenantId: string,
    @Query('since') since?: string,
    @Query('limit') limit?: string,
  ) {
    const limitNum = limit ? parseInt(limit) : 50;
    return this.inspectionService.getInspections(tenantId, since, limitNum);
  }
}