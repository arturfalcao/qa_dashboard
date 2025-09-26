import {
  CallHandler,
  ExecutionContext,
  Injectable,
  NestInterceptor,
} from "@nestjs/common";
import { Observable } from "rxjs";
import { tap } from "rxjs/operators";
import { TracingService } from "./tracing.service";

@Injectable()
export class TracingInterceptor implements NestInterceptor {
  constructor(private readonly tracingService: TracingService) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const http = context.switchToHttp();
    const request = http.getRequest();
    if (!request) {
      return next.handle();
    }

    const traceContext = this.tracingService.createTraceContext();
    const traceparent = `00-${traceContext.traceId}-${traceContext.spanId}-01`;
    request.traceId = traceContext.traceId;
    request.spanId = traceContext.spanId;
    request.headers["traceparent"] = request.headers["traceparent"] || traceparent;

    const response = http.getResponse();

    return this.tracingService.runWithContext(traceContext, () =>
      next.handle().pipe(
        tap(() => {
          if (response?.setHeader) {
            response.setHeader("traceparent", traceparent);
          }
        }),
      ),
    );
  }
}
