import { randomUUID } from "crypto";

import { Injectable, NotFoundException } from "@nestjs/common";

import {
  DeviceCommandType,
  DeviceStatus,
  EdgeEventType,
  OperatorAssignLotPayload,
  OperatorCommandResult,
  OperatorDevice,
  OperatorDeviceDetail,
  OperatorFlagPayload,
  OperatorLotFeedItem,
  OperatorLotSummary,
  OperatorReprintPayload,
  QueueDepthSample,
} from "@qa-dashboard/shared";

import { OperatorRealtimeService } from "./operator-realtime.service";

interface DeviceState {
  device: OperatorDevice;
  events: OperatorLotFeedItem[];
  queueDepthHistory: QueueDepthSample[];
}

interface LotMetadata {
  lotId: string;
  lotCode: string;
  styleRef: string;
  customer: string;
}

@Injectable()
export class OperatorService {
  private readonly devices = new Map<string, DeviceState>();
  private readonly lotMetadata = new Map<string, LotMetadata>();
  private readonly commands: OperatorCommandResult[] = [];

  constructor(private readonly realtime: OperatorRealtimeService) {
    this.seed();
  }

  getDevices(site?: string): OperatorDevice[] {
    return Array.from(this.iterateDeviceStates(site)).map((state) => this.cloneDevice(state));
  }

  getDeviceDetail(deviceId: string): OperatorDeviceDetail {
    const state = this.devices.get(deviceId);
    if (!state) {
      throw new NotFoundException(`Device ${deviceId} not found`);
    }

    const recentEvents = state.events.slice(0, 20).map((event) => this.cloneEvent(event));
    const latestEvent = recentEvents[0];

    const metrics = {
      pieceSequence: latestEvent?.pieceSequence ?? 0,
      qaIndicators: latestEvent?.qaMetrics
        ? { ...latestEvent.qaMetrics }
        : { status: "ok" as const },
      lastTranscript: latestEvent?.transcript ?? null,
    };

    return {
      ...this.cloneDevice(state),
      metrics,
      recentEvents,
      queueDepthHistory: state.queueDepthHistory.slice(-24).map((sample) => ({ ...sample })),
    };
  }

  assignLotToDevice(deviceId: string, payload: OperatorAssignLotPayload): OperatorDeviceDetail {
    const state = this.devices.get(deviceId);
    if (!state) {
      throw new NotFoundException(`Device ${deviceId} not found`);
    }

    const assignedAt = new Date().toISOString();
    state.device.currentAssignment = {
      ...payload,
      assignedAt,
      assignedBy: "cloud.supervisor@demo",
    };

    const metadata = this.resolveLotMetadata(payload.lotId, payload.styleRef, payload.customer);

    const event: OperatorLotFeedItem = {
      id: randomUUID(),
      lotId: metadata.lotId,
      deviceId,
      type: EdgeEventType.FLAG,
      timestamp: assignedAt,
      transcript: `Lot switched to ${metadata.lotCode}`,
      qaMetrics: {
        status: "ok",
      },
      flag: {
        note: `Assignment updated to ${metadata.styleRef} / ${metadata.customer}`,
        createdAt: assignedAt,
        createdBy: "system",
        severity: "info",
      },
    };

    state.events.unshift(event);
    if (state.events.length > 100) {
      state.events.length = 100;
    }

    this.realtime.emitDeviceAssignmentChanged(state.device);
    this.realtime.emitLotFeedUpdated(event);

    return this.getDeviceDetail(deviceId);
  }

  issueReprintCommand(deviceId: string, payload: OperatorReprintPayload): OperatorCommandResult {
    const state = this.devices.get(deviceId);
    if (!state) {
      throw new NotFoundException(`Device ${deviceId} not found`);
    }

    const command: OperatorCommandResult = {
      commandId: randomUUID(),
      deviceId,
      type: DeviceCommandType.REPRINT_LABEL,
      status: "QUEUED",
      createdAt: new Date().toISOString(),
    };

    this.commands.push(command);

    const acknowledgementEvent: OperatorLotFeedItem = {
      id: randomUUID(),
      lotId: payload.lotId,
      deviceId,
      type: EdgeEventType.PRINT_LABEL,
      timestamp: command.createdAt,
      transcript: `Reprint requested for piece #${payload.pieceSeq}`,
      qaMetrics: {
        status: "ok",
      },
    };

    state.events.unshift(acknowledgementEvent);
    if (state.events.length > 100) {
      state.events.length = 100;
    }

    this.realtime.emitCommandQueued(command);
    this.realtime.emitLotFeedUpdated(acknowledgementEvent);

    return command;
  }

  getActiveLots(site?: string): OperatorLotSummary[] {
    const summaries = new Map<string, OperatorLotSummary>();

    for (const state of this.iterateDeviceStates(site)) {
      for (const event of state.events) {
        const metadata = this.resolveLotMetadata(event.lotId);
        const summary = summaries.get(event.lotId) ?? {
          lotId: metadata.lotId,
          lotCode: metadata.lotCode,
          customer: metadata.customer,
          styleRef: metadata.styleRef,
          activeDeviceIds: [],
          piecesInspected: 0,
          defectsFound: 0,
          defectRate: 0,
          lastEventAt: null as string | null,
        };

        if (!summary.activeDeviceIds.includes(event.deviceId)) {
          summary.activeDeviceIds.push(event.deviceId);
        }

        if (typeof event.pieceSequence === "number") {
          summary.piecesInspected = Math.max(summary.piecesInspected, event.pieceSequence);
        }

        if (event.type === EdgeEventType.DEFECT) {
          summary.defectsFound += 1;
        }

        summary.lastEventAt = event.timestamp;
        summaries.set(event.lotId, summary);
      }
    }

    return Array.from(summaries.values())
      .map((summary) => ({
        ...summary,
        defectRate:
          summary.piecesInspected > 0
            ? Number((summary.defectsFound / summary.piecesInspected).toFixed(3))
            : 0,
      }))
      .sort((a, b) => (b.lastEventAt ?? "").localeCompare(a.lastEventAt ?? ""));
  }

  getLotFeed(lotId: string, site?: string): OperatorLotFeedItem[] {
    const events: OperatorLotFeedItem[] = [];

    for (const state of this.iterateDeviceStates(site)) {
      for (const event of state.events) {
        if (event.lotId === lotId) {
          events.push(this.cloneEvent(event));
        }
      }
    }

    return events.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
  }

  createFlag(lotId: string, payload: OperatorFlagPayload): OperatorLotFeedItem {
    for (const state of this.devices.values()) {
      const event = state.events.find((item) => item.id === payload.eventId && item.lotId === lotId);
      if (event) {
        const now = new Date().toISOString();
        event.flag = {
          note: payload.note,
          createdAt: now,
          createdBy: "operator.cloud",
          severity: payload.severity ?? "info",
        };

        this.realtime.emitLotFeedUpdated(event);
        return this.cloneEvent(event);
      }
    }

    throw new NotFoundException(`Event ${payload.eventId} not found for lot ${lotId}`);
  }

  private iterateDeviceStates(site?: string): Iterable<DeviceState> {
    return Array.from(this.devices.values()).filter((state) =>
      site ? state.device.site.toLowerCase() === site.toLowerCase() : true,
    );
  }

  private cloneDevice(state: DeviceState): OperatorDevice {
    return {
      ...state.device,
      currentAssignment: state.device.currentAssignment
        ? { ...state.device.currentAssignment }
        : null,
    };
  }

  private cloneEvent(event: OperatorLotFeedItem): OperatorLotFeedItem {
    return {
      ...event,
      qaMetrics: event.qaMetrics ? { ...event.qaMetrics } : undefined,
      flag: event.flag ? { ...event.flag } : undefined,
    };
  }

  private resolveLotMetadata(lotId: string, styleRef?: string, customer?: string): LotMetadata {
    const existing = this.lotMetadata.get(lotId);
    if (existing) {
      return existing;
    }

    const metadata: LotMetadata = {
      lotId,
      lotCode: lotId.toUpperCase(),
      styleRef: styleRef ?? "Unknown",
      customer: customer ?? "Unknown",
    };

    this.lotMetadata.set(lotId, metadata);
    return metadata;
  }

  private seed(): void {
    const now = new Date();
    const minute = 60 * 1000;

    const lotA: LotMetadata = {
      lotId: "lot-001",
      lotCode: "LOT-001",
      styleRef: "ST-001",
      customer: "Atelier Norte",
    };

    const lotB: LotMetadata = {
      lotId: "lot-002",
      lotCode: "LOT-002",
      styleRef: "ST-104",
      customer: "Green Threads",
    };

    [lotA, lotB].forEach((lot) => this.lotMetadata.set(lot.lotId, lot));

    const deviceStates: DeviceState[] = [
      {
        device: {
          id: "device-1",
          name: "North Line A",
          site: "Porto",
          status: DeviceStatus.ONLINE,
          lastSeenAt: new Date(now.getTime() - 30 * 1000).toISOString(),
          queueDepth: 1,
          firmwareVersion: "1.4.2",
          ipAddress: "10.0.0.21",
          currentAssignment: {
            lotId: lotA.lotId,
            styleRef: lotA.styleRef,
            customer: lotA.customer,
            assignedAt: new Date(now.getTime() - 5 * minute).toISOString(),
            assignedBy: "ops.lead@demo",
          },
        },
        events: [
          {
            id: randomUUID(),
            lotId: lotA.lotId,
            deviceId: "device-1",
            type: EdgeEventType.PHOTO,
            timestamp: new Date(now.getTime() - 2 * minute).toISOString(),
            pieceSequence: 128,
            thumbnailUrl: "https://placehold.co/280x280?text=Lot+001",
            transcript: "Piece 128 captured",
            qaMetrics: {
              pixelsPerMillimeter: 5.2,
              sharpnessScore: 0.92,
              brightnessScore: 0.76,
              status: "ok",
            },
          },
          {
            id: randomUUID(),
            lotId: lotA.lotId,
            deviceId: "device-1",
            type: EdgeEventType.DEFECT,
            timestamp: new Date(now.getTime() - 4 * minute).toISOString(),
            pieceSequence: 127,
            thumbnailUrl: "https://placehold.co/280x280?text=Defect",
            defectText: "Loose thread near collar",
            qaMetrics: {
              pixelsPerMillimeter: 5.1,
              sharpnessScore: 0.81,
              brightnessScore: 0.72,
              status: "warning",
            },
          },
          {
            id: randomUUID(),
            lotId: lotA.lotId,
            deviceId: "device-1",
            type: EdgeEventType.PIECE_END,
            timestamp: new Date(now.getTime() - 6 * minute).toISOString(),
            pieceSequence: 126,
            transcript: "Piece complete",
            qaMetrics: {
              status: "ok",
            },
          },
        ],
        queueDepthHistory: Array.from({ length: 6 }).map((_, index) => ({
          timestamp: new Date(now.getTime() - index * minute).toISOString(),
          depth: Math.max(0, 3 - index),
        })),
      },
      {
        device: {
          id: "device-2",
          name: "North Line B",
          site: "Porto",
          status: DeviceStatus.DEGRADED,
          lastSeenAt: new Date(now.getTime() - 4 * minute).toISOString(),
          queueDepth: 4,
          firmwareVersion: "1.3.9",
          ipAddress: "10.0.0.22",
          currentAssignment: {
            lotId: lotB.lotId,
            styleRef: lotB.styleRef,
            customer: lotB.customer,
            assignedAt: new Date(now.getTime() - 45 * minute).toISOString(),
            assignedBy: "ops.lead@demo",
          },
        },
        events: [
          {
            id: randomUUID(),
            lotId: lotB.lotId,
            deviceId: "device-2",
            type: EdgeEventType.PHOTO,
            timestamp: new Date(now.getTime() - 3 * minute).toISOString(),
            pieceSequence: 88,
            thumbnailUrl: "https://placehold.co/280x280?text=Lot+002",
            transcript: "Piece 88 captured",
            qaMetrics: {
              pixelsPerMillimeter: 4.8,
              sharpnessScore: 0.7,
              brightnessScore: 0.69,
              status: "warning",
            },
          },
          {
            id: randomUUID(),
            lotId: lotB.lotId,
            deviceId: "device-2",
            type: EdgeEventType.HEARTBEAT,
            timestamp: new Date(now.getTime() - 5 * minute).toISOString(),
            qaMetrics: {
              status: "ok",
            },
          },
        ],
        queueDepthHistory: Array.from({ length: 6 }).map((_, index) => ({
          timestamp: new Date(now.getTime() - index * minute).toISOString(),
          depth: Math.max(1, 4 - index),
        })),
      },
      {
        device: {
          id: "device-3",
          name: "South Pilot",
          site: "Guimarães",
          status: DeviceStatus.OFFLINE,
          lastSeenAt: new Date(now.getTime() - 60 * minute).toISOString(),
          queueDepth: 0,
          firmwareVersion: "1.4.0",
          ipAddress: "10.0.1.10",
          currentAssignment: null,
        },
        events: [],
        queueDepthHistory: Array.from({ length: 6 }).map((_, index) => ({
          timestamp: new Date(now.getTime() - index * minute).toISOString(),
          depth: 0,
        })),
      },
    ];

    deviceStates.forEach((state) => {
      this.devices.set(state.device.id, state);
      if (state.device.currentAssignment) {
        this.resolveLotMetadata(
          state.device.currentAssignment.lotId,
          state.device.currentAssignment.styleRef,
          state.device.currentAssignment.customer,
        );
      }
      state.events.forEach((event) => {
        this.resolveLotMetadata(event.lotId);
      });
    });
  }
}
