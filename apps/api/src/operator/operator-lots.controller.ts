import { Body, Controller, Get, Param, Post, Query } from "@nestjs/common";

import { OperatorService } from "./operator.service";
import { CreateFlagDto } from "./dto/create-flag.dto";

@Controller("operator/lots")
export class OperatorLotsController {
  constructor(private readonly operatorService: OperatorService) {}

  @Get("active")
  getActiveLots(@Query("site") site?: string) {
    return this.operatorService.getActiveLots(site);
  }

  @Get(":id/feed")
  getLotFeed(@Param("id") lotId: string, @Query("site") site?: string) {
    return this.operatorService.getLotFeed(lotId, site);
  }

  @Post(":id/flags")
  createFlag(@Param("id") lotId: string, @Body() payload: CreateFlagDto) {
    return this.operatorService.createFlag(lotId, payload);
  }
}
