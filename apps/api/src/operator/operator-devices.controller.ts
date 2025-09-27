import { Body, Controller, Get, Param, Post, Query } from "@nestjs/common";

import { OperatorService } from "./operator.service";
import { AssignLotDto } from "./dto/assign-lot.dto";
import { ReprintCommandDto } from "./dto/reprint-command.dto";

@Controller("operator/devices")
export class OperatorDevicesController {
  constructor(private readonly operatorService: OperatorService) {}

  @Get()
  getDevices(@Query("site") site?: string) {
    return this.operatorService.getDevices(site);
  }

  @Get(":id")
  getDevice(@Param("id") id: string) {
    return this.operatorService.getDeviceDetail(id);
  }

  @Post(":id/assign")
  assignLot(@Param("id") id: string, @Body() payload: AssignLotDto) {
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
