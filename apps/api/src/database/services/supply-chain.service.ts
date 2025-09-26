import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { SupplyChainRole } from "../entities/supply-chain-role.entity";

@Injectable()
export class SupplyChainService {
  constructor(
    @InjectRepository(SupplyChainRole)
    private readonly supplyChainRoleRepository: Repository<SupplyChainRole>,
  ) {}

  async listRoles(): Promise<SupplyChainRole[]> {
    return this.supplyChainRoleRepository.find({
      order: { defaultSequence: "ASC", name: "ASC" },
    });
  }
}
