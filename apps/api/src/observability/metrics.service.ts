import { Injectable } from "@nestjs/common";

interface RequestMetricKey {
  method: string;
  path: string;
  status: number;
}

interface RequestMetricValue {
  count: number;
  totalDurationMs: number;
}

@Injectable()
export class MetricsService {
  private readonly requestMetrics = new Map<string, RequestMetricValue>();
  private readonly startTime = Date.now();

  recordHttpRequest(
    method: string,
    path: string,
    status: number,
    durationMs: number,
  ): void {
    const key: RequestMetricKey = { method, path, status };
    const mapKey = this.serializeKey(key);
    const existing = this.requestMetrics.get(mapKey) || {
      count: 0,
      totalDurationMs: 0,
    };
    existing.count += 1;
    existing.totalDurationMs += durationMs;
    this.requestMetrics.set(mapKey, existing);
  }

  renderMetrics(): string {
    const uptimeSeconds = (Date.now() - this.startTime) / 1000;
    const lines: string[] = [];
    lines.push("# HELP app_uptime_seconds Application uptime in seconds");
    lines.push("# TYPE app_uptime_seconds counter");
    lines.push(`app_uptime_seconds ${uptimeSeconds.toFixed(0)}`);

    lines.push("# HELP app_http_requests_total Total HTTP requests processed");
    lines.push("# TYPE app_http_requests_total counter");

    lines.push("# HELP app_http_request_duration_ms Average HTTP request duration in ms");
    lines.push("# TYPE app_http_request_duration_ms gauge");

    for (const [key, value] of this.requestMetrics.entries()) {
      const labels = JSON.parse(key) as RequestMetricKey;
      const avgDuration = value.totalDurationMs / value.count;
      const labelString = this.serializeLabels(labels);
      lines.push(`app_http_requests_total${labelString} ${value.count}`);
      lines.push(
        `app_http_request_duration_ms${labelString} ${avgDuration.toFixed(2)}`,
      );
    }

    return lines.join("\n") + "\n";
  }

  private serializeKey(key: RequestMetricKey): string {
    return JSON.stringify({
      method: key.method.toUpperCase(),
      path: key.path,
      status: key.status,
    });
  }

  private serializeLabels(key: RequestMetricKey): string {
    const safePath = key.path.replace(/"/g, '\\"');
    return `{method="${key.method.toUpperCase()}",path="${safePath}",status="${key.status}"}`;
  }
}
