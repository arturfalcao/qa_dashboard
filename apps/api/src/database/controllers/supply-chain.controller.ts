import { Controller, Get } from "@nestjs/common";
import { ApiOperation, ApiTags } from "@nestjs/swagger";
import { SupplyChainService } from "../services/supply-chain.service";

@ApiTags("supply-chain")
@Controller("supply-chain")
export class SupplyChainController {
  constructor(private readonly supplyChainService: SupplyChainService) {}

  @Get("roles")
  @ApiOperation({ summary: "List available supply chain roles" })
  async listRoles() {
    return this.supplyChainService.listRoles();
  }
}
