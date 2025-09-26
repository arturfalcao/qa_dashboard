import {
  CallHandler,
  ExecutionContext,
  Injectable,
  NestInterceptor,
} from "@nestjs/common";
import { Observable } from "rxjs";
import { tap } from "rxjs/operators";
import { MetricsService } from "./metrics.service";

@Injectable()
export class MetricsInterceptor implements NestInterceptor {
  constructor(private readonly metricsService: MetricsService) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const start = Date.now();
    const http = context.switchToHttp();
    const request = http.getRequest();

    return next.handle().pipe(
      tap({
        next: () => this.record(http, request, start),
        error: () => this.record(http, request, start, true),
      }),
    );
  }

  private record(http: any, request: any, start: number, isError = false) {
    const response = http.getResponse();
    const duration = Date.now() - start;
    const status = isError ? response?.statusCode ?? 500 : response?.statusCode ?? 200;
    const method = request?.method || "UNKNOWN";
    const path = (request?.route?.path || request?.originalUrl || request?.url || "unknown").replace(/\?.*$/, "");

    this.metricsService.recordHttpRequest(method, path, status, duration);
  }
}
