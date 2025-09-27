import { Module } from "@nestjs/common";
import { TypeOrmModule } from "@nestjs/typeorm";
import { DppController } from "./dpp.controller";
import { DppService } from "./dpp.service";
import { Dpp } from "../database/entities/dpp.entity";
import { DppEvent } from "../database/entities/dpp-event.entity";
import { DppAccessLog } from "../database/entities/dpp-access-log.entity";
import { Lot } from "../database/entities/lot.entity";

@Module({
  imports: [
    TypeOrmModule.forFeature([Dpp, DppEvent, DppAccessLog, Lot]),
  ],
  controllers: [DppController],
  providers: [DppService],
  exports: [DppService, TypeOrmModule],
})
export class DppModule {}