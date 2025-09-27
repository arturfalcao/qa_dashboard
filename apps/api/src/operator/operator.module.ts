import { Module } from "@nestjs/common";

import { OperatorService } from "./operator.service";
import { OperatorDevicesController } from "./operator-devices.controller";
import { OperatorLotsController } from "./operator-lots.controller";
import { OperatorRealtimeService } from "./operator-realtime.service";

@Module({
  controllers: [OperatorDevicesController, OperatorLotsController],
  providers: [OperatorService, OperatorRealtimeService],
  exports: [OperatorService],
})
export class OperatorModule {}
