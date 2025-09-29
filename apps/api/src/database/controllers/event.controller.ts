import { Controller, Get, Query } from "@nestjs/common";
import {
  ApiTags,
  ApiOperation,
  ApiQuery,
} from "@nestjs/swagger";
import { EventService } from "../services/event.service";
import { ClientId } from "../../common/decorators";

@ApiTags("events")
@Controller("events")
export class EventController {
  constructor(private eventService: EventService) {}

  @Get()
  @ApiOperation({ summary: "Get events for client" })
  @ApiQuery({ name: "since", required: false, description: "ISO date string" })
  @ApiQuery({
    name: "limit",
    required: false,
    type: Number,
    description: "Limit results",
  })
  async getEvents(
    @ClientId() tenantId: string,
    @Query("since") since?: string,
    @Query("limit") limit?: string,
  ) {
    const limitNum = limit ? parseInt(limit) : 100;
    return this.eventService.getEvents(tenantId, since, limitNum);
  }
}
