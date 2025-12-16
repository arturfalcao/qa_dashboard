import { Module } from "@nestjs/common";
import { ConfigModule } from "@nestjs/config";
import { TypeOrmModule } from "@nestjs/typeorm";
import { TechPackService } from "./tech-pack.service";
import { TechPackCrudService } from "./tech-pack-crud.service";
import { TechPackController } from "./tech-pack.controller";
import { StorageModule } from "../storage/storage.module";
import { TechPack } from "../database/entities/tech-pack.entity";
import { Lot } from "../database/entities/lot.entity";

@Module({
  imports: [
    ConfigModule,
    StorageModule,
    TypeOrmModule.forFeature([TechPack, Lot]),
  ],
  controllers: [TechPackController],
  providers: [TechPackService, TechPackCrudService],
  exports: [TechPackService, TechPackCrudService],
})
export class TechPackModule {}