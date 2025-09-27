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
        "PA&CO Luxury Manufacturing": {
          admin: "carlos.martins@paco.example / demo1234",
          operations: "joana.costa@paco.example / demo1234",
          clevel: "ines.azevedo@paco.example / demo1234",
          viewer: "miguel.lopes@paco.example / demo1234",
        },
      },
    };
  }
}
