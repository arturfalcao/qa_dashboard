import { Module } from "@nestjs/common";
import { MetricsService } from "./metrics.service";
import { MetricsController } from "./metrics.controller";
import { TracingService } from "./tracing.service";
import { TracingInterceptor } from "./tracing.interceptor";
import { LoggerInterceptor } from "./logger.interceptor";
import { MetricsInterceptor } from "./metrics.interceptor";

@Module({
  controllers: [MetricsController],
  providers: [
    MetricsService,
    TracingService,
    TracingInterceptor,
    LoggerInterceptor,
    MetricsInterceptor,
  ],
  exports: [MetricsService, TracingService, TracingInterceptor, LoggerInterceptor, MetricsInterceptor],
})
export class ObservabilityModule {}
