import { IsNumber, IsOptional, IsString, Min } from "class-validator";

import { OperatorReprintPayload } from "@qa-dashboard/shared";

export class ReprintCommandDto implements OperatorReprintPayload {
  @IsString()
  lotId!: string;

  @IsNumber()
  @Min(0)
  pieceSeq!: number;

  @IsOptional()
  @IsString()
  reason?: string;
}
