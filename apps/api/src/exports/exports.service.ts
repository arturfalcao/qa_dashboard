import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { Inspection } from "../database/entities/inspection.entity";
import { Batch } from "../database/entities/batch.entity";
import { StorageService } from "../storage/storage.service";
import { AnalyticsService } from "../database/services/analytics.service";
import * as puppeteer from "puppeteer";
import * as fs from "fs/promises";
import * as path from "path";

@Injectable()
export class ExportsService {
  constructor(
    @InjectRepository(Inspection)
    private inspectionRepository: Repository<Inspection>,
    @InjectRepository(Batch)
    private batchRepository: Repository<Batch>,
    private storageService: StorageService,
    private analyticsService: AnalyticsService,
  ) {}

  async generatePDF(
    tenantId: string,
    batchId?: string,
    range?: "last_7d" | "last_30d",
  ): Promise<string> {
    let whereClause = { tenantId };
    let title = "QA Dashboard Report";

    if (batchId) {
      const batch = await this.batchRepository.findOne({
        where: { id: batchId, tenantId },
        relations: ["vendor", "style"],
      });
      if (!batch) {
        throw new Error("Batch not found");
      }
      title = `Batch Report - ${batch.poNumber}`;
      whereClause = { ...whereClause, garment: { batchId } } as any;
    } else if (range) {
      const days = range === "last_7d" ? 7 : 30;
      const since = new Date();
      since.setDate(since.getDate() - days);
      whereClause = { ...whereClause, inspectedAt: { $gte: since } } as any;
      title = `QA Report - Last ${days} Days`;
    }

    // Get data
    const [defectRate, throughput, defectTypes, approvalTime] =
      await Promise.all([
        this.analyticsService.getDefectRate(tenantId, range || "last_7d"),
        this.analyticsService.getThroughput(
          tenantId,
          "day",
          range || "last_7d",
        ),
        this.analyticsService.getDefectTypes(tenantId, range || "last_7d"),
        this.analyticsService.getApprovalTime(tenantId, range || "last_7d"),
      ]);

    const inspections = await this.inspectionRepository.find({
      where: whereClause,
      relations: [
        "garment",
        "garment.batch",
        "garment.batch.vendor",
        "garment.batch.style",
      ],
      order: { inspectedAt: "DESC" },
      take: 100,
    });

    // Generate HTML content
    const htmlContent = this.generatePDFTemplate({
      title,
      defectRate,
      throughput,
      defectTypes,
      approvalTime,
      inspections,
      generatedAt: new Date().toISOString(),
    });

    // Generate PDF using Puppeteer
    const browser = await puppeteer.launch({ headless: "new" });
    const page = await browser.newPage();
    await page.setContent(htmlContent, { waitUntil: "networkidle0" });

    const pdfBuffer = await page.pdf({
      format: "A4",
      printBackground: true,
      margin: {
        top: "1cm",
        right: "1cm",
        bottom: "1cm",
        left: "1cm",
      },
    });

    await browser.close();

    // Upload to storage
    const key = this.storageService.generateKey(
      tenantId,
      `report-${Date.now()}.pdf`,
    );
    await this.storageService.uploadFileWithKey(
      key,
      pdfBuffer,
      "application/pdf",
    );

    // Return presigned URL
    return await this.storageService.getPresignedDownloadUrl(key);
  }

  async generateCSV(
    tenantId: string,
    range?: "last_7d" | "last_30d",
  ): Promise<string> {
    let whereClause = { tenantId };

    if (range) {
      const days = range === "last_7d" ? 7 : 30;
      const since = new Date();
      since.setDate(since.getDate() - days);
      whereClause = { ...whereClause, inspectedAt: { $gte: since } } as any;
    }

    const inspections = await this.inspectionRepository.find({
      where: whereClause,
      relations: [
        "garment",
        "garment.batch",
        "garment.batch.vendor",
        "garment.batch.style",
      ],
      order: { inspectedAt: "DESC" },
    });

    // Generate CSV content
    const csvHeader =
      [
        "Inspection ID",
        "Garment Serial",
        "Batch PO",
        "Vendor",
        "Style",
        "Size",
        "Color",
        "Has Defect",
        "Defect Type",
        "Notes",
        "Inspected At",
      ].join(",") + "\n";

    const csvRows = inspections
      .map(
        (inspection) =>
          [
            inspection.id,
            inspection.garment?.serial || "",
            inspection.garment?.batch?.poNumber || "",
            inspection.garment?.batch?.vendor?.name || "",
            inspection.garment?.batch?.style?.styleCode || "",
            inspection.garment?.size || "",
            inspection.garment?.color || "",
            inspection.hasDefect ? "Yes" : "No",
            inspection.defectType || "",
            (inspection.notes || "").replace(/,/g, ";").replace(/\n/g, " "),
            inspection.inspectedAt.toISOString(),
          ]
            .map((field) => `"${field}"`)
            .join(",") + "\n",
      )
      .join("");

    const csvContent = csvHeader + csvRows;
    const csvBuffer = Buffer.from(csvContent, "utf-8");

    // Upload to storage
    const key = this.storageService.generateKey(
      tenantId,
      `export-${Date.now()}.csv`,
    );
    await this.storageService.uploadFileWithKey(key, csvBuffer, "text/csv");

    // Return presigned URL
    return await this.storageService.getPresignedDownloadUrl(key);
  }

  private generatePDFTemplate(data: any): string {
    const defectRateOverall = data.defectRate.data.find(
      (d) => d.name === "Overall",
    ) || { defectRate: 0, totalInspected: 0, totalDefects: 0 };

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>${data.title}</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            color: #333;
          }
          .header {
            text-align: center;
            border-bottom: 2px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
          }
          .header h1 {
            margin: 0;
            color: #007bff;
          }
          .header p {
            margin: 10px 0 0 0;
            color: #666;
          }
          .metrics {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 30px;
          }
          .metric-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
          }
          .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 5px;
          }
          .metric-label {
            color: #666;
            font-size: 0.9em;
          }
          .section {
            margin-bottom: 30px;
          }
          .section h2 {
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
            color: #333;
          }
          .defect-types {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 15px;
          }
          .defect-type {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            text-align: center;
          }
          .defect-count {
            font-weight: bold;
            color: #dc3545;
          }
          .footer {
            margin-top: 50px;
            text-align: center;
            color: #666;
            font-size: 0.8em;
            border-top: 1px solid #ddd;
            padding-top: 20px;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>${data.title}</h1>
          <p>Generated on ${new Date(data.generatedAt).toLocaleString()}</p>
        </div>

        <div class="metrics">
          <div class="metric-card">
            <div class="metric-value">${defectRateOverall.defectRate.toFixed(1)}%</div>
            <div class="metric-label">Defect Rate</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${defectRateOverall.totalInspected}</div>
            <div class="metric-label">Total Inspected</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${data.approvalTime.average.toFixed(1)}h</div>
            <div class="metric-label">Avg Approval Time</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${data.throughput.data.reduce((sum, d) => sum + d.inspections, 0)}</div>
            <div class="metric-label">Total Inspections</div>
          </div>
        </div>

        <div class="section">
          <h2>Defect Type Breakdown</h2>
          <div class="defect-types">
            ${data.defectTypes.data
              .map(
                (defect) => `
              <div class="defect-type">
                <div class="defect-count">${defect.count}</div>
                <div>${defect.type}</div>
                <div>${defect.percentage.toFixed(1)}%</div>
              </div>
            `,
              )
              .join("")}
          </div>
        </div>

        <div class="section">
          <h2>Recent Inspections</h2>
          <p>Showing last ${data.inspections.length} inspections</p>
        </div>

        <div class="footer">
          <p>🤖 Generated with QA Dashboard</p>
        </div>
      </body>
      </html>
    `;
  }
}
