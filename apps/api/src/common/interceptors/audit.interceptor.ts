import {
  CallHandler,
  ExecutionContext,
  Injectable,
  NestInterceptor,
} from "@nestjs/common";
import { Observable } from "rxjs";
import { tap } from "rxjs/operators";
import { DataSource } from "typeorm";
import { AuditLog } from "../../database/entities/audit-log.entity";

@Injectable()
export class AuditInterceptor implements NestInterceptor {
  constructor(private readonly dataSource: DataSource) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const ctx = context.switchToHttp();
    const request = ctx.getRequest();

    if (!request) {
      return next.handle();
    }

    const method = request.method?.toUpperCase();
    const isMutating = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
    if (!isMutating) {
      return next.handle();
    }

    const { user, params, body } = request;
    const entity = request.route?.path || request.url;
    const entityId = params?.id || params?.batchId || params?.lotId || null;

    return next.handle().pipe(
      tap(async () => {
        try {
          await this.dataSource.manager.insert(AuditLog, {
            userId: user?.userId || user?.id || null,
            entity,
            entityId: entityId ?? "N/A",
            action: method,
            before: null,
            after: body ? (body as Record<string, unknown>) : null,
          });
        } catch (error) {
          // eslint-disable-next-line no-console
          console.error("[AuditInterceptor] failed to record audit log", error);
        }
      }),
    );
  }
}
