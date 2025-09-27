import { IsIn, IsOptional, IsString } from "class-validator";

import { OperatorFlagPayload } from "@qa-dashboard/shared";

const FLAG_SEVERITIES = ["info", "warning", "critical"] as const;

export class CreateFlagDto implements OperatorFlagPayload {
  @IsString()
  eventId!: string;

  @IsString()
  note!: string;

  @IsOptional()
  @IsIn(FLAG_SEVERITIES)
  severity?: "info" | "warning" | "critical";
}
