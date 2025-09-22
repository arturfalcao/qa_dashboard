import { Controller, Get, Query, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth, ApiQuery } from '@nestjs/swagger';
import { EventService } from '../services/event.service';
import { JwtAuthGuard } from '../../auth/jwt-auth.guard';
import { TenantId, Public } from '../../common/decorators';

@ApiTags('events')
@Controller('events')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class EventController {
  constructor(private eventService: EventService) {}

  @Get()
  @Public()
  @ApiOperation({ summary: 'Get events for tenant' })
  @ApiQuery({ name: 'since', required: false, description: 'ISO date string' })
  @ApiQuery({ name: 'limit', required: false, type: Number, description: 'Limit results' })
  async getEvents(
    @TenantId() tenantId: string,
    @Query('since') since?: string,
    @Query('limit') limit?: string,
  ) {
    const limitNum = limit ? parseInt(limit) : 100;
    // For demo purposes, use first tenant if no tenantId available
    const finalTenantId = tenantId || '045f1210-98cc-457e-9d44-982a1875527d';
    return this.eventService.getEvents(finalTenantId, since, limitNum);
  }
}