import { Injectable } from "@nestjs/common";
import { AsyncLocalStorage } from "async_hooks";
import { randomUUID } from "crypto";

export interface TraceContext {
  traceId: string;
  spanId: string;
}

@Injectable()
export class TracingService {
  private readonly storage = new AsyncLocalStorage<TraceContext>();

  runWithContext<T>(context: TraceContext, callback: () => Promise<T>): Promise<T>;
  runWithContext<T>(context: TraceContext, callback: () => T): T;
  runWithContext<T>(context: TraceContext, callback: () => T | Promise<T>): T | Promise<T> {
    return this.storage.run(context, callback);
  }

  getCurrentTrace(): TraceContext | null {
    return this.storage.getStore() ?? null;
  }

  createTraceContext(): TraceContext {
    const traceId = randomUUID().replace(/-/g, "");
    const spanId = randomUUID().replace(/-/g, "").substring(0, 16);
    return { traceId, spanId };
  }
}
