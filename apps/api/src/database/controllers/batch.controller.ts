import { Controller, Get, Post, Param, Body, UseGuards, ForbiddenException } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiBearerAuth } from '@nestjs/swagger';
import { BatchService } from '../services/batch.service';
import { JwtAuthGuard } from '../../auth/jwt-auth.guard';
import { TenantId, CurrentUser } from '../../common/decorators';
import { ApprovalDto, RejectDto, ApprovalSchema, RejectSchema, UserRole } from '@qa-dashboard/shared';
import { ZodValidationPipe } from '../../common/zod-validation.pipe';

@ApiTags('batches')
@Controller('batches')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class BatchController {
  constructor(private batchService: BatchService) {}

  @Get()
  @ApiOperation({ summary: 'Get batches for tenant' })
  async getBatches(@TenantId() tenantId: string) {
    return this.batchService.getBatches(tenantId);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get batch by ID' })
  async getBatchById(
    @TenantId() tenantId: string,
    @Param('id') id: string,
  ) {
    return this.batchService.getBatchById(tenantId, id);
  }

  @Post(':id/approve')
  @ApiOperation({ summary: 'Approve batch' })
  async approveBatch(
    @TenantId() tenantId: string,
    @Param('id') id: string,
    @CurrentUser() user: any,
    @Body(new ZodValidationPipe(ApprovalSchema)) approvalDto: ApprovalDto,
  ) {
    if (user.role !== UserRole.CLIENT_ADMIN) {
      throw new ForbiddenException('Only client admins can approve batches');
    }

    await this.batchService.approveBatch(
      tenantId,
      id,
      user.userId,
      user.role,
      approvalDto.comment,
    );

    return { message: 'Batch approved successfully' };
  }

  @Post(':id/reject')
  @ApiOperation({ summary: 'Reject batch' })
  async rejectBatch(
    @TenantId() tenantId: string,
    @Param('id') id: string,
    @CurrentUser() user: any,
    @Body(new ZodValidationPipe(RejectSchema)) rejectDto: RejectDto,
  ) {
    if (user.role !== UserRole.CLIENT_ADMIN) {
      throw new ForbiddenException('Only client admins can reject batches');
    }

    await this.batchService.rejectBatch(
      tenantId,
      id,
      user.userId,
      user.role,
      rejectDto.comment,
    );

    return { message: 'Batch rejected successfully' };
  }
}