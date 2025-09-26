import { Module } from "@nestjs/common";
import { ConfigModule } from "@nestjs/config";
import { TypeOrmModule } from "@nestjs/typeorm";
import { PassportModule } from "@nestjs/passport";
import { APP_INTERCEPTOR, APP_GUARD } from "@nestjs/core";

import { AuthModule } from "./auth/auth.module";
import { JwtAuthGuard } from "./auth/jwt-auth.guard";
import { DatabaseModule } from "./database/database.module";
import { StorageModule } from "./storage/storage.module";
import { ExportsModule } from "./exports/exports.module";
import { DppModule } from "./dpp/dpp.module";
import { ReportsModule } from "./reports/reports.module";
import { ObservabilityModule } from "./observability/observability.module";
import { AuditInterceptor } from "./common/interceptors/audit.interceptor";
import { TracingInterceptor } from "./observability/tracing.interceptor";
import { MetricsInterceptor } from "./observability/metrics.interceptor";
import { LoggerInterceptor } from "./observability/logger.interceptor";

import dataSourceOptions from "./database/typeorm.config";

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    TypeOrmModule.forRoot(dataSourceOptions),
    AuthModule,
    DatabaseModule,
    StorageModule,
    ObservabilityModule,
    ExportsModule,
    DppModule,
    ReportsModule,
  ],
  providers: [
    {
      provide: APP_GUARD,
      useClass: JwtAuthGuard,
    },
    {
      provide: APP_INTERCEPTOR,
      useClass: TracingInterceptor,
    },
    {
      provide: APP_INTERCEPTOR,
      useClass: MetricsInterceptor,
    },
    {
      provide: APP_INTERCEPTOR,
      useClass: LoggerInterceptor,
    },
    {
      provide: APP_INTERCEPTOR,
      useClass: AuditInterceptor,
    },
  ],
})
export class AppModule {}
