import { Injectable, NotFoundException } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { Inspection } from "../database/entities/inspection.entity";
import { Lot } from "../database/entities/lot.entity";
import { StorageService } from "../storage/storage.service";
import { AnalyticsService } from "../database/services/analytics.service";
import * as puppeteer from "puppeteer";

@Injectable()
export class ExportsService {
  constructor(
    @InjectRepository(Inspection)
    private readonly inspectionRepository: Repository<Inspection>,
    @InjectRepository(Lot)
    private readonly lotRepository: Repository<Lot>,
    private readonly storageService: StorageService,
    private readonly analyticsService: AnalyticsService,
  ) {}

  async generatePDF(
    clientId: string,
    lotId?: string,
    range?: "last_7d" | "last_30d",
  ): Promise<string> {
    if (!clientId) {
      throw new NotFoundException("Client not provided");
    }

    const lot = lotId
      ? await this.lotRepository.findOne({
          where: { id: lotId, clientId },
          relations: ["factory"],
        })
      : await this.lotRepository.findOne({
          where: { clientId },
          order: { updatedAt: "DESC" },
          relations: ["factory"],
        });

    if (!lot) {
      throw new NotFoundException("Lot not found");
    }

    const inspections = await this.inspectionRepository.find({
      where: { lotId: lot.id },
      relations: [
        "defects",
        "defects.defectType",
        "defects.photos",
        "inspector",
      ],
      order: { createdAt: "DESC" },
    });

    const [defectRate, throughput, defectTypes, approvalTime] = await Promise.all([
      this.analyticsService.getDefectRate(clientId, range || "last_7d", "factory"),
      this.analyticsService.getThroughput(clientId, "day", range || "last_7d"),
      this.analyticsService.getDefectTypes(clientId, range || "last_7d"),
      this.analyticsService.getApprovalTime(clientId, range || "last_7d"),
    ]);

    const htmlContent = this.buildLotReportHtml({
      lot,
      inspections,
      defectRate,
      throughput,
      defectTypes,
      approvalTime,
    });

    const browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();
    await page.setContent(htmlContent, { waitUntil: "networkidle0" });
    const pdfBuffer = await page.pdf({ format: "A4", printBackground: true });
    await browser.close();

    const key = this.storageService.generateKey(
      clientId,
      `lot-${lot.id}-${Date.now()}.pdf`,
      "reports",
    );
    await this.storageService.uploadFileWithKey(
      key,
      pdfBuffer,
      "application/pdf",
      "reports",
    );

    return this.storageService.getPresignedDownloadUrl(key, "reports");
  }

  async generateCSV(
    clientId: string,
    range?: "last_7d" | "last_30d",
  ): Promise<string> {
    if (!clientId) {
      throw new NotFoundException("Client not provided");
    }

    const since = range === "last_30d"
      ? new Date(Date.now() - 1000 * 60 * 60 * 24 * 30)
      : new Date(Date.now() - 1000 * 60 * 60 * 24 * 7);

    const inspections = await this.inspectionRepository
      .createQueryBuilder("inspection")
      .innerJoinAndSelect("inspection.lot", "lot")
      .leftJoinAndSelect("lot.factory", "factory")
      .leftJoinAndSelect("inspection.defects", "defect")
      .leftJoinAndSelect("defect.defectType", "defectType")
      .where("lot.clientId = :clientId", { clientId })
      .andWhere("inspection.createdAt >= :since", { since })
      .orderBy("inspection.createdAt", "DESC")
      .getMany();

    const header = [
      "Inspection ID",
      "Lot",
      "Factory",
      "Inspector",
      "Started At",
      "Finished At",
      "Defect Count",
    ];

    const rows = inspections.map((inspection) => [
      inspection.id,
      inspection.lot.styleRef,
      inspection.lot.factory?.name || "",
      inspection.inspector?.email || "",
      inspection.startedAt?.toISOString() || "",
      inspection.finishedAt?.toISOString() || "",
      inspection.defects?.length || 0,
    ]);

    const csv = [header.join(","), ...rows.map((row) => row.join(","))].join("\n");
    const buffer = Buffer.from(csv, "utf-8");

    const key = this.storageService.generateKey(
      clientId,
      `inspections-${Date.now()}.csv`,
      "reports",
    );
    await this.storageService.uploadFileWithKey(key, buffer, "text/csv", "reports");

    return this.storageService.getPresignedDownloadUrl(key, "reports");
  }

  private buildLotReportHtml(data: {
    lot: Lot;
    inspections: Inspection[];
    defectRate: any;
    throughput: any;
    defectTypes: any;
    approvalTime: any;
  }): string {
    const { lot, inspections, defectRate, throughput, defectTypes, approvalTime } = data;
    const inspectionRows = inspections
      .map((inspection) => {
        const defects = inspection.defects
          ?.map(
            (defect) =>
              `<li><strong>${defect.defectType?.name || "Unclassified"}</strong> - ${
                defect.note || ""
              }</li>`,
          )
          .join("") || "<li>No defects recorded</li>";

        return `
          <section class="inspection">
            <h3>Inspection ${inspection.id}</h3>
            <p><strong>Inspector:</strong> ${inspection.inspector?.email || "Unassigned"}</p>
            <p><strong>Window:</strong> ${
              inspection.startedAt?.toISOString() || "–"
            } → ${inspection.finishedAt?.toISOString() || "–"}</p>
            <p><strong>Defects:</strong></p>
            <ul>${defects}</ul>
          </section>
        `;
      })
      .join("\n");

    return `
      <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; padding: 24px; color: #1f2933; }
            h1 { margin-bottom: 0; }
            h2 { margin-top: 32px; }
            .metrics { display: flex; gap: 16px; margin-top: 16px; }
            .metric-card { flex: 1; background: #f1f5f9; padding: 16px; border-radius: 8px; }
            .inspection { margin-top: 24px; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; }
          </style>
        </head>
        <body>
          <h1>Lot Report • ${lot.styleRef}</h1>
          <p><strong>Factory:</strong> ${lot.factory?.name || "Unknown"}</p>
          <p><strong>Status:</strong> ${lot.status}</p>
          <p><strong>Quantity:</strong> ${lot.quantityTotal}</p>
          <div class="metrics">
            <div class="metric-card">
              <h3>Defect Rate</h3>
              <p>${lot.defectRate.toFixed(2)}%</p>
            </div>
            <div class="metric-card">
              <h3>Progress</h3>
              <p>${lot.inspectedProgress.toFixed(2)}%</p>
            </div>
            <div class="metric-card">
              <h3>Approval Lead Time</h3>
              <p>${approvalTime.average}h avg</p>
            </div>
          </div>
          <section>
            <h2>Recent Inspections</h2>
            ${inspectionRows}
          </section>
          <section>
            <h2>Defect Breakdown</h2>
            <ul>
              ${defectTypes.data
                .map((entry: any) => `<li>${entry.type}: ${entry.count}</li>`)
                .join("")}
            </ul>
          </section>
        </body>
      </html>
    `;
  }
}
