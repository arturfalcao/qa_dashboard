import { Module } from "@nestjs/common";
import { ConfigModule } from "@nestjs/config";
import { TechPackService } from "./tech-pack.service";
import { StorageModule } from "../storage/storage.module";

@Module({
  imports: [ConfigModule, StorageModule],
  providers: [TechPackService],
  exports: [TechPackService],
})
export class TechPackModule {}