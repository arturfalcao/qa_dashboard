import { IsString } from "class-validator";

import { OperatorAssignLotPayload } from "@qa-dashboard/shared";

export class AssignLotDto implements OperatorAssignLotPayload {
  @IsString()
  lotId!: string;

  @IsString()
  styleRef!: string;

  @IsString()
  customer!: string;
}
