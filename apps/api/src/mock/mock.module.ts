import { Module } from "@nestjs/common";
import { MockService } from "./mock.service";
import { MockController } from "./mock.controller";
import { DatabaseModule } from "../database/database.module";
import { StorageModule } from "../storage/storage.module";

@Module({
  imports: [DatabaseModule, StorageModule],
  providers: [MockService],
  controllers: [MockController],
  exports: [MockService],
})
export class MockModule {}
