import { Injectable, Logger } from "@nestjs/common";

import {
  OperatorDevice,
  OperatorCommandResult,
  OperatorLotFeedItem,
} from "@qa-dashboard/shared";

@Injectable()
export class OperatorRealtimeService {
  private readonly logger = new Logger(OperatorRealtimeService.name);

  emitDeviceAssignmentChanged(device: OperatorDevice): void {
    this.logger.log(
      `Device ${device.id} assignment changed to ${device.currentAssignment?.lotId ?? "none"}`,
    );
  }

  emitCommandQueued(command: OperatorCommandResult): void {
    this.logger.log(
      `Command ${command.commandId} queued for device ${command.deviceId} (${command.type})`,
    );
  }

  emitLotFeedUpdated(event: OperatorLotFeedItem): void {
    this.logger.log(
      `New ${event.type} event recorded for lot ${event.lotId} on device ${event.deviceId}`,
    );
  }
}
