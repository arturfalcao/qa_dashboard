import { Controller, Post, Get } from "@nestjs/common";
import { ApiTags, ApiOperation } from "@nestjs/swagger";
import { MockService } from "./mock.service";
import { Public } from "../common/decorators";

@ApiTags("mock")
@Controller("mock")
export class MockController {
  constructor(private mockService: MockService) {}

  @Post("inspections/start")
  @Public()
  @ApiOperation({ summary: "Start mock inspection generator (dev only)" })
  async startInspections() {
    await this.mockService.startInspectionGenerator();
    return { message: "Mock inspection generator started" };
  }

  @Post("inspections/stop")
  @Public()
  @ApiOperation({ summary: "Stop mock inspection generator (dev only)" })
  async stopInspections() {
    await this.mockService.stopInspectionGenerator();
    return { message: "Mock inspection generator stopped" };
  }

  @Get("inspections/status")
  @Public()
  @ApiOperation({ summary: "Get mock generator status" })
  async getStatus() {
    return this.mockService.getGeneratorStatus();
  }
}
