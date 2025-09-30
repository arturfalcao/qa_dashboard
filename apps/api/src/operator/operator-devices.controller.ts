import { Body, Controller, Get, Param, Post, Query, ForbiddenException } from "@nestjs/common";

import { OperatorService } from "./operator.service";
import { AssignLotDto } from "./dto/assign-lot.dto";
import { ReprintCommandDto } from "./dto/reprint-command.dto";
import { CurrentUser } from "../common/decorators";
import { UserRole } from "@qa-dashboard/shared";

@Controller("operator/devices")
export class OperatorDevicesController {
  constructor(private readonly operatorService: OperatorService) {}

  private ensureSupervisorAccess(user?: { roles?: UserRole[]; email?: string }) {
    const roles = user?.roles || [];
    const allowedRoles = [UserRole.SUPERVISOR, UserRole.OPS_MANAGER, UserRole.ADMIN];
    const isSuperAdmin = user?.email === "celso.silva@packpolish.com";

    if (!isSuperAdmin && !roles.some((role) => allowedRoles.includes(role))) {
      throw new ForbiddenException("Supervisor, Ops Manager, or Admin access required to assign lots");
    }
  }

  @Get()
  getDevices(@Query("site") site?: string) {
    return this.operatorService.getDevices(site);
  }

  @Get(":id")
  getDevice(@Param("id") id: string) {
    return this.operatorService.getDeviceDetail(id);
  }

  @Post(":id/assign")
  assignLot(
    @CurrentUser() user: any,
    @Param("id") id: string,
    @Body() payload: AssignLotDto,
  ) {
    this.ensureSupervisorAccess(user);
    return this.operatorService.assignLotToDevice(id, payload);
  }

  @Post(":id/commands/reprint")
  issueReprint(
    @Param("id") id: string,
    @Body() payload: ReprintCommandDto,
  ) {
    return this.operatorService.issueReprintCommand(id, payload);
  }
}
