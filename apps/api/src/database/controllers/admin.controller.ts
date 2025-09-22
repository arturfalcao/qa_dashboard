import { Controller, Post } from "@nestjs/common";
import { ApiTags, ApiOperation } from "@nestjs/swagger";
import { SeedService } from "../services/seed.service";
import { Public } from "../../common/decorators";

@ApiTags("admin")
@Controller("admin")
export class AdminController {
  constructor(private seedService: SeedService) {}

  @Post("seed")
  @Public()
  @ApiOperation({ summary: "Seed database with demo data (dev only)" })
  async seed() {
    await this.seedService.seedData();
    return {
      message: "Database seeded successfully",
      credentials: {
        "Tenant A (heymarly)": {
          admin: "admin@marly.example / demo1234",
          viewer: "viewer@marly.example / demo1234",
        },
        "Tenant B (samplebrand)": {
          admin: "admin@brand.example / demo1234",
          viewer: "viewer@brand.example / demo1234",
        },
      },
    };
  }
}
