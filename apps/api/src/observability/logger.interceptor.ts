import {
  CallHandler,
  ExecutionContext,
  Injectable,
  NestInterceptor,
} from "@nestjs/common";
import { Observable } from "rxjs";
import { tap } from "rxjs/operators";
import { TracingService } from "./tracing.service";

interface LogPayload {
  level: string;
  time: number;
  message: string;
  traceId?: string;
  spanId?: string;
  [key: string]: unknown;
}

@Injectable()
export class LoggerInterceptor implements NestInterceptor {
  constructor(private readonly tracingService: TracingService) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const http = context.switchToHttp();
    const request = http.getRequest();
    const start = Date.now();

    const logBase: Partial<LogPayload> = {
      level: "info",
      method: request?.method,
      path: request?.originalUrl || request?.url,
    };

    const traceContext = this.tracingService.getCurrentTrace();
    if (traceContext) {
      logBase.traceId = traceContext.traceId;
      logBase.spanId = traceContext.spanId;
    }

    this.log({
      ...logBase,
      message: "request_received",
      time: Date.now(),
    });

    return next.handle().pipe(
      tap({
        next: () => this.logResponse(logBase, start, http),
        error: (err) => this.logResponse(logBase, start, http, err),
      }),
    );
  }

  private logResponse(
    base: Partial<LogPayload>,
    start: number,
    http: ReturnType<ExecutionContext["switchToHttp"]>,
    error?: unknown,
  ) {
    const response = http.getResponse();
    const duration = Date.now() - start;
    const statusCode = response?.statusCode ?? (error ? 500 : 200);

    this.log({
      ...base,
      message: error ? "request_error" : "request_completed",
      statusCode,
      durationMs: duration,
      error: error instanceof Error ? error.message : error,
      time: Date.now(),
    });
  }

  private log(payload: Partial<LogPayload>) {
    const logEntry: LogPayload = {
      level: payload.level ?? "info",
      time: payload.time ?? Date.now(),
      message: payload.message ?? "log",
      traceId: payload.traceId as string | undefined,
      spanId: payload.spanId as string | undefined,
      ...payload,
    };
    console.log(JSON.stringify(logEntry));
  }
}
