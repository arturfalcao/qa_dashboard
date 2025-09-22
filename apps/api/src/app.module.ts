import { Module } from "@nestjs/common";
import { ConfigModule } from "@nestjs/config";
import { TypeOrmModule } from "@nestjs/typeorm";
import { JwtModule } from "@nestjs/jwt";
import { PassportModule } from "@nestjs/passport";
import { APP_GUARD } from "@nestjs/core";

import { AuthModule } from "./auth/auth.module";
import { DatabaseModule } from "./database/database.module";
import { StorageModule } from "./storage/storage.module";
import { MockModule } from "./mock/mock.module";
import { ExportsModule } from "./exports/exports.module";
import { JwtAuthGuard } from "./auth/jwt-auth.guard";

import { Tenant } from "./database/entities/tenant.entity";
import { User } from "./database/entities/user.entity";
import { Vendor } from "./database/entities/vendor.entity";
import { Style } from "./database/entities/style.entity";
import { Batch } from "./database/entities/batch.entity";
import { Garment } from "./database/entities/garment.entity";
import { Inspection } from "./database/entities/inspection.entity";
import { Approval } from "./database/entities/approval.entity";
import { Event } from "./database/entities/event.entity";
import { InspectionPhoto } from "./database/entities/inspection-photo.entity";
import { PhotoAnnotation } from "./database/entities/photo-annotation.entity";

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    TypeOrmModule.forRoot({
      type: "postgres",
      url: process.env.DATABASE_URL,
      entities: [
        Tenant,
        User,
        Vendor,
        Style,
        Batch,
        Garment,
        Inspection,
        Approval,
        Event,
        InspectionPhoto,
        PhotoAnnotation,
      ],
      synchronize: false,
      logging: process.env.NODE_ENV === "development",
    }),
    PassportModule,
    JwtModule.register({
      secret: process.env.JWT_SECRET || "your-jwt-secret",
      signOptions: { expiresIn: "15m" },
    }),
    AuthModule,
    DatabaseModule,
    StorageModule,
    MockModule,
    ExportsModule,
  ],
  providers: [
    {
      provide: APP_GUARD,
      useClass: JwtAuthGuard,
    },
  ],
})
export class AppModule {}
