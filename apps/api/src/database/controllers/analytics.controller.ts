import { Controller, Get, Query } from "@nestjs/common";
import {
  ApiTags,
  ApiOperation,
  ApiQuery,
} from "@nestjs/swagger";
import { AnalyticsService } from "../services/analytics.service";
import { ClientId } from "../../common/decorators";

@ApiTags("analytics")
@Controller("analytics")
export class AnalyticsController {
  constructor(private analyticsService: AnalyticsService) {}

  @Get("defect-rate")
  @ApiOperation({ summary: "Get defect rate analytics" })
  @ApiQuery({ name: "groupBy", required: false, enum: ["style", "factory"] })
  @ApiQuery({ name: "range", required: false, enum: ["last_7d", "last_30d"] })
  async getDefectRate(
    @ClientId() tenantId: string,
    @Query("groupBy") groupBy?: "style" | "factory",
    @Query("range") range?: "last_7d" | "last_30d",
  ) {
    return this.analyticsService.getDefectRate(
      tenantId,
      range || "last_7d",
      groupBy,
    );
  }

  @Get("throughput")
  @ApiOperation({ summary: "Get throughput analytics" })
  @ApiQuery({ name: "bucket", required: false, enum: ["day", "week"] })
  @ApiQuery({ name: "range", required: false, enum: ["last_7d", "last_30d"] })
  async getThroughput(
    @ClientId() tenantId: string,
    @Query("bucket") bucket?: "day" | "week",
    @Query("range") range?: "last_7d" | "last_30d",
  ) {
    return this.analyticsService.getThroughput(
      tenantId,
      bucket || "day",
      range || "last_7d",
    );
  }

  @Get("defect-types")
  @ApiOperation({ summary: "Get defect type breakdown" })
  @ApiQuery({ name: "range", required: false, enum: ["last_7d", "last_30d"] })
  async getDefectTypes(
    @ClientId() tenantId: string,
    @Query("range") range?: "last_7d" | "last_30d",
  ) {
    return this.analyticsService.getDefectTypes(
      tenantId,
      range || "last_7d",
    );
  }

  @Get("approval-time")
  @ApiOperation({ summary: "Get approval time analytics" })
  @ApiQuery({ name: "range", required: false, enum: ["last_7d", "last_30d"] })
  async getApprovalTime(
    @ClientId() tenantId: string,
    @Query("range") range?: "last_7d" | "last_30d",
  ) {
    return this.analyticsService.getApprovalTime(
      tenantId,
      range || "last_7d",
    );
  }
}
