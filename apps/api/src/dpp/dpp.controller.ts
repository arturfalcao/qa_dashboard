import {
  Controller,
  Get,
  Post,
  Patch,
  Param,
  Body,
  Query,
  Req,
  Res,
  NotFoundException,
  BadRequestException,
  UseGuards,
} from "@nestjs/common";
import { ApiTags, ApiOperation, ApiResponse, ApiQuery, ApiParam } from "@nestjs/swagger";
import { Request, Response } from "express";
import { DppService } from "./dpp.service";
import { Public, ClientId, CurrentUser } from "../common/decorators";
import { CreateDppSchema, UpdateDppSchema, CreateEventSchema } from "./dpp-schemas";
import { ZodValidationPipe } from "../common/zod-validation.pipe";
import { DppStatus } from "../database/entities/dpp.entity";
import { DppAccessView } from "../database/entities/dpp-access-log.entity";
import { UserRole } from "@qa-dashboard/shared";
import { launchPuppeteer } from "../common/puppeteer";

@ApiTags("dpp")
@Controller("dpp")
export class DppController {
  constructor(private readonly dppService: DppService) {}

  private getClientIpAndUserAgent(req: Request) {
    const ip = req.ip || req.connection.remoteAddress || "unknown";
    const userAgent = req.get("User-Agent");
    return { ip, userAgent };
  }

  private getBaseUrl(req: Request): string {
    return `${req.protocol}://${req.get("host")}`;
  }

  @Post()
  @ApiOperation({ summary: "Create a new DPP" })
  @ApiResponse({ status: 201, description: "DPP created successfully" })
  async createDpp(
    @ClientId() clientId: string,
    @CurrentUser() user: { userId: string; roles: UserRole[] },
    @Body(new ZodValidationPipe(CreateDppSchema)) body: any,
  ) {
    // Check permissions
    if (!user.roles.some(role => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role))) {
      throw new BadRequestException("Insufficient permissions to create DPP");
    }

    return await this.dppService.createDpp(clientId, user.userId, body);
  }

  @Patch(":id")
  @ApiOperation({ summary: "Update a DPP" })
  @ApiParam({ name: "id", description: "DPP ID" })
  async updateDpp(
    @Param("id") id: string,
    @ClientId() clientId: string,
    @CurrentUser() user: { roles: UserRole[] },
    @Body(new ZodValidationPipe(UpdateDppSchema)) body: any,
  ) {
    // Check permissions
    if (!user.roles.some(role => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role))) {
      throw new BadRequestException("Insufficient permissions to update DPP");
    }

    return await this.dppService.updateDpp(id, clientId, body);
  }

  @Post(":id/publish")
  @ApiOperation({ summary: "Publish a DPP" })
  @ApiParam({ name: "id", description: "DPP ID" })
  async publishDpp(
    @Param("id") id: string,
    @ClientId() clientId: string,
    @CurrentUser() user: { userId: string; roles: UserRole[] },
  ) {
    // Check permissions
    if (!user.roles.some(role => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role))) {
      throw new BadRequestException("Insufficient permissions to publish DPP");
    }

    return await this.dppService.publishDpp(id, clientId, user.userId);
  }

  @Public()
  @Get(":id")
  @ApiOperation({ summary: "Get public DPP view (HTML)" })
  @ApiParam({ name: "id", description: "DPP ID" })
  @ApiQuery({ name: "view", required: false, description: "View type (restricted requires auth)" })
  async getDpp(
    @Param("id") id: string,
    @Req() req: Request,
    @Res() res: Response,
    @Query("view") view?: string,
    @ClientId() clientId?: string,
    @CurrentUser() user?: { userId: string; roles: UserRole[] },
  ) {
    const { ip, userAgent } = this.getClientIpAndUserAgent(req);

    if (view === "restricted") {
      // Restricted view requires authentication
      if (!user || !clientId) {
        throw new BadRequestException("Authentication required for restricted view");
      }

      const restrictedData = await this.dppService.getRestrictedDpp(id, clientId, user.roles);

      // Log restricted access
      await this.dppService.logAccess(id, DppAccessView.RESTRICTED, {
        ip,
        userAgent,
        userId: user.userId,
        endpoint: req.url,
      });

      return res.json(restrictedData);
    }

    // Public view
    const result = await this.dppService.getPublicDpp(id);
    if (!result) {
      throw new NotFoundException("DPP not found or not published");
    }

    // Log public access
    await this.dppService.logAccess(id, DppAccessView.PUBLIC, {
      ip,
      userAgent,
      endpoint: req.url,
    });

    // Return HTML view
    const html = this.generatePublicHtml(result.publicData, this.getBaseUrl(req));
    res.set("Content-Type", "text/html");
    res.send(html);
  }

  @Public()
  @Get(":id.json")
  @ApiOperation({ summary: "Get public DPP JSON" })
  @ApiParam({ name: "id", description: "DPP ID" })
  async getPublicDppJson(
    @Param("id") rawId: string,
    @Req() req: Request,
  ) {
    // Remove .json extension if present
    const id = rawId.replace(/\.json$/, '');
    const { ip, userAgent } = this.getClientIpAndUserAgent(req);

    const result = await this.dppService.getPublicDpp(id);
    if (!result) {
      throw new NotFoundException("DPP not found or not published");
    }

    // Log public access
    await this.dppService.logAccess(id, DppAccessView.PUBLIC, {
      ip,
      userAgent,
      endpoint: req.url,
    });

    return result.publicData;
  }

  @Public()
  @Get(":id.qr")
  @ApiOperation({ summary: "Get QR code for DPP" })
  @ApiParam({ name: "id", description: "DPP ID" })
  async getDppQr(
    @Param("id") rawId: string,
    @Req() req: Request,
    @Res() res: Response,
  ) {
    // Remove .qr extension if present
    const id = rawId.replace(/\.qr$/, '');
    // Verify DPP exists and is published
    const result = await this.dppService.getPublicDpp(id);
    if (!result) {
      throw new NotFoundException("DPP not found or not published");
    }

    const baseUrl = this.getBaseUrl(req);
    const qrBuffer = await this.dppService.generateQrCode(id, baseUrl);

    res.set({
      "Content-Type": "image/png",
      "Content-Length": qrBuffer.length,
      "Cache-Control": "public, max-age=3600", // Cache for 1 hour
    });

    res.send(qrBuffer);
  }

  @Public()
  @Get(":id.pdf")
  @ApiOperation({ summary: "Get PDF export of public DPP data" })
  @ApiParam({ name: "id", description: "DPP ID" })
  async getDppPdf(
    @Param("id") rawId: string,
    @Req() req: Request,
    @Res() res: Response,
  ) {
    // Remove .pdf extension if present
    const id = rawId.replace(/\.pdf$/, '');
    const { ip, userAgent } = this.getClientIpAndUserAgent(req);

    const result = await this.dppService.getPublicDpp(id);
    if (!result) {
      throw new NotFoundException("DPP not found or not published");
    }

    // Log public access
    await this.dppService.logAccess(id, DppAccessView.PUBLIC, {
      ip,
      userAgent,
      endpoint: req.url,
    });

    // Generate professional PDF content
    const pdfContent = await this.generateBasicPdf(result.publicData);

    res.set({
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="dpp-${id}.pdf"`,
    });

    res.send(pdfContent);
  }

  @Post(":id/ingest/lot/:lotId")
  @ApiOperation({ summary: "Ingest data from a lot into the DPP" })
  @ApiParam({ name: "id", description: "DPP ID" })
  @ApiParam({ name: "lotId", description: "Lot ID to ingest from" })
  async ingestFromLot(
    @Param("id") id: string,
    @Param("lotId") lotId: string,
    @ClientId() clientId: string,
    @CurrentUser() user: { roles: UserRole[] },
  ) {
    // Check permissions
    if (!user.roles.some(role => [UserRole.ADMIN, UserRole.OPS_MANAGER].includes(role))) {
      throw new BadRequestException("Insufficient permissions to ingest data");
    }

    return await this.dppService.ingestFromLot(id, lotId, clientId);
  }

  @Post(":id/events")
  @ApiOperation({ summary: "Create a new event for the DPP" })
  @ApiParam({ name: "id", description: "DPP ID" })
  async createEvent(
    @Param("id") id: string,
    @ClientId() clientId: string,
    @CurrentUser() user: { userId: string; roles: UserRole[] },
    @Body(new ZodValidationPipe(CreateEventSchema)) body: any,
  ) {
    // Verify DPP exists and belongs to client
    await this.dppService.getDppForClient(id, clientId);

    return await this.dppService.createEvent(id, body);
  }

  @Get(":id/events")
  @ApiOperation({ summary: "Get events for the DPP" })
  @ApiParam({ name: "id", description: "DPP ID" })
  async getEvents(
    @Param("id") id: string,
    @ClientId() clientId: string,
  ) {
    return await this.dppService.getDppEvents(id, clientId);
  }

  @Get(":id/access-logs")
  @ApiOperation({ summary: "Get access logs for the DPP" })
  @ApiParam({ name: "id", description: "DPP ID" })
  @ApiQuery({ name: "limit", required: false, description: "Limit number of logs returned" })
  async getAccessLogs(
    @Param("id") id: string,
    @ClientId() clientId: string,
    @CurrentUser() user: { roles: UserRole[] },
    @Query("limit") limit?: string,
  ) {
    // Check permissions - only admins can view access logs
    if (!user.roles.some(role => [UserRole.ADMIN].includes(role))) {
      throw new BadRequestException("Insufficient permissions to view access logs");
    }

    const limitNum = limit ? parseInt(limit, 10) : 100;
    return await this.dppService.getDppAccessLogs(id, clientId, limitNum);
  }

  @Get()
  @ApiOperation({ summary: "List DPPs for the client" })
  @ApiQuery({ name: "status", required: false, description: "Filter by status" })
  async listDpps(
    @ClientId() clientId: string,
    @Query("status") status?: DppStatus,
  ) {
    return await this.dppService.listDpps(clientId, status);
  }

  private generatePublicHtml(data: any, baseUrl: string): string {
    const product = data.product || {};
    const materials = data.materials || [];
    const care = data.care || {};
    const sustainability = data.sustainability || {};
    const endOfLife = data.end_of_life || {};

    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${product.brand || 'Product'} - Digital Product Passport</title>
    <meta name="description" content="Digital Product Passport for ${product.brand} ${product.styleRef}">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .product-title { font-size: 2em; margin-bottom: 10px; }
        .product-subtitle { color: #666; font-size: 1.2em; }
        .section { margin-bottom: 30px; padding: 20px; background: #f9f9f9; border-radius: 8px; }
        .section h2 { margin-bottom: 15px; color: #2c5aa0; }
        .materials-list { list-style: none; }
        .materials-list li { padding: 5px 0; }
        .care-instructions { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
        .care-item { padding: 10px; background: white; border-radius: 4px; }
        .links { text-align: center; margin-top: 30px; }
        .links a { display: inline-block; margin: 0 10px; padding: 10px 20px; background: #2c5aa0; color: white; text-decoration: none; border-radius: 4px; }
        .footer { text-align: center; margin-top: 50px; color: #666; font-size: 0.9em; }
        @media (max-width: 600px) {
            .container { padding: 15px; }
            .product-title { font-size: 1.5em; }
            .care-instructions { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="product-title">${product.brand || ''} ${product.styleRef || ''}</h1>
            <p class="product-subtitle">SKU: ${product.sku || 'N/A'}</p>
            ${product.gtin ? `<p class="product-subtitle">GTIN: ${product.gtin}</p>` : ''}
        </div>

        <div class="section">
            <h2>Product Information</h2>
            <p><strong>Brand:</strong> ${product.brand || 'N/A'}</p>
            <p><strong>Style Reference:</strong> ${product.styleRef || 'N/A'}</p>
            <p><strong>SKU:</strong> ${product.sku || 'N/A'}</p>
        </div>

        ${materials.length > 0 ? `
        <div class="section">
            <h2>Materials</h2>
            <ul class="materials-list">
                ${materials.map(material => `
                    <li><strong>${material.percent}% ${material.fiber}</strong>${material.certs && material.certs.length > 0 ? ` (${material.certs.join(', ')})` : ''}</li>
                `).join('')}
            </ul>
        </div>
        ` : ''}

        ${Object.keys(care).length > 0 ? `
        <div class="section">
            <h2>Care Instructions</h2>
            <div class="care-instructions">
                ${care.wash ? `<div class="care-item"><strong>Wash:</strong> ${care.wash}</div>` : ''}
                ${care.dry ? `<div class="care-item"><strong>Dry:</strong> ${care.dry}</div>` : ''}
                ${care.iron ? `<div class="care-item"><strong>Iron:</strong> ${care.iron}</div>` : ''}
                ${care.repair ? `<div class="care-item"><strong>Repair:</strong> ${care.repair}</div>` : ''}
            </div>
        </div>
        ` : ''}

        ${sustainability.highlights && sustainability.highlights.length > 0 ? `
        <div class="section">
            <h2>Sustainability</h2>
            <ul>
                ${sustainability.highlights.map(highlight => `<li>${highlight}</li>`).join('')}
            </ul>
            ${sustainability.certifications && sustainability.certifications.length > 0 ? `
                <p><strong>Certifications:</strong> ${sustainability.certifications.join(', ')}</p>
            ` : ''}
        </div>
        ` : ''}

        ${Object.keys(endOfLife).length > 0 ? `
        <div class="section">
            <h2>End of Life</h2>
            ${endOfLife.reuse ? `<p><strong>Reuse:</strong> ${endOfLife.reuse}</p>` : ''}
            ${endOfLife.recycle ? `<p><strong>Recycle:</strong> ${endOfLife.recycle}</p>` : ''}
            ${endOfLife.contact ? `<p><strong>Contact:</strong> ${endOfLife.contact}</p>` : ''}
        </div>
        ` : ''}

        <div class="links">
            <a href="${baseUrl}/dpp/${data.id}.json">JSON Data</a>
            <a href="${baseUrl}/dpp/${data.id}.pdf">Download PDF</a>
        </div>

        <div class="footer">
            <p>Digital Product Passport • Updated ${new Date(data.updatedAt).toLocaleDateString()}</p>
        </div>
    </div>
</body>
</html>
    `.trim();
  }

  private async generateBasicPdf(data: any): Promise<Buffer> {
    // Generate HTML for PDF
    const html = this.generatePdfHtml(data);

    // Use puppeteer to generate PDF
    const browser = await launchPuppeteer({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
      const page = await browser.newPage();
      await page.setContent(html, { waitUntil: 'networkidle0' });

      const pdfBuffer = await page.pdf({
        format: 'A4',
        margin: {
          top: '20px',
          bottom: '20px',
          left: '20px',
          right: '20px'
        },
        printBackground: true,
        displayHeaderFooter: true,
        headerTemplate: '<div></div>',
        footerTemplate: `
          <div style="font-size: 10px; text-align: center; width: 100%; color: #666;">
            Digital Product Passport • Generated on <span class="date"></span> • Page <span class="pageNumber"></span> of <span class="totalPages"></span>
          </div>
        `
      });

      return pdfBuffer;
    } finally {
      await browser.close();
    }
  }

  private generatePdfHtml(data: any): string {
    const product = data.product || {};
    const materials = data.materials || [];
    const care = data.care || {};
    const sustainability = data.sustainability || {};
    const endOfLife = data.end_of_life || {};

    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Digital Product Passport - ${product.brand} ${product.styleRef}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: white;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 20px 0;
            border-bottom: 3px solid #2c5aa0;
        }
        .logo {
            font-size: 28px;
            font-weight: bold;
            color: #2c5aa0;
            margin-bottom: 10px;
        }
        .product-title {
            font-size: 24px;
            margin-bottom: 5px;
            color: #333;
        }
        .product-subtitle {
            color: #666;
            font-size: 14px;
        }
        .section {
            margin-bottom: 30px;
            page-break-inside: avoid;
        }
        .section h2 {
            font-size: 18px;
            margin-bottom: 15px;
            color: #2c5aa0;
            border-left: 4px solid #2c5aa0;
            padding-left: 10px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .info-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 3px solid #2c5aa0;
        }
        .info-item strong {
            color: #2c5aa0;
        }
        .materials-list {
            list-style: none;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
        }
        .materials-list li {
            padding: 8px 0;
            border-bottom: 1px solid #ddd;
        }
        .materials-list li:last-child {
            border-bottom: none;
        }
        .care-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        .care-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 3px solid #28a745;
        }
        .care-item strong {
            color: #28a745;
        }
        .sustainability-list {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 3px solid #28a745;
        }
        .sustainability-list li {
            margin-bottom: 8px;
        }
        .certifications {
            margin-top: 15px;
            padding: 10px;
            background: #e8f5e8;
            border-radius: 3px;
        }
        .footer {
            margin-top: 40px;
            text-align: center;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #ddd;
            padding-top: 20px;
        }
        @media print {
            body { print-color-adjust: exact; }
            .section { page-break-inside: avoid; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">Digital Product Passport</div>
        <h1 class="product-title">${product.brand || ''} ${product.styleRef || ''}</h1>
        <p class="product-subtitle">SKU: ${product.sku || 'N/A'} ${product.gtin ? `• GTIN: ${product.gtin}` : ''}</p>
    </div>

    <div class="section">
        <h2>Product Information</h2>
        <div class="info-grid">
            <div class="info-item">
                <strong>Brand:</strong><br>
                ${product.brand || 'N/A'}
            </div>
            <div class="info-item">
                <strong>Style Reference:</strong><br>
                ${product.styleRef || 'N/A'}
            </div>
            <div class="info-item">
                <strong>SKU:</strong><br>
                ${product.sku || 'N/A'}
            </div>
            <div class="info-item">
                <strong>GTIN:</strong><br>
                ${product.gtin || 'Not specified'}
            </div>
        </div>
    </div>

    ${materials.length > 0 ? `
    <div class="section">
        <h2>Materials Composition</h2>
        <ul class="materials-list">
            ${materials.map(material => `
                <li>
                    <strong>${material.percent}% ${material.fiber}</strong>
                    ${material.certs && material.certs.length > 0 ? `<br><small>Certifications: ${material.certs.join(', ')}</small>` : ''}
                </li>
            `).join('')}
        </ul>
    </div>
    ` : ''}

    ${Object.keys(care).length > 0 ? `
    <div class="section">
        <h2>Care Instructions</h2>
        <div class="care-grid">
            ${care.wash ? `<div class="care-item"><strong>Washing:</strong><br>${care.wash}</div>` : ''}
            ${care.dry ? `<div class="care-item"><strong>Drying:</strong><br>${care.dry}</div>` : ''}
            ${care.iron ? `<div class="care-item"><strong>Ironing:</strong><br>${care.iron}</div>` : ''}
            ${care.repair ? `<div class="care-item"><strong>Repair:</strong><br>${care.repair}</div>` : ''}
        </div>
    </div>
    ` : ''}

    ${sustainability.highlights && sustainability.highlights.length > 0 ? `
    <div class="section">
        <h2>Sustainability</h2>
        <div class="sustainability-list">
            <ul>
                ${sustainability.highlights.map(highlight => `<li>${highlight}</li>`).join('')}
            </ul>
            ${sustainability.certifications && sustainability.certifications.length > 0 ? `
                <div class="certifications">
                    <strong>Certifications:</strong> ${sustainability.certifications.join(', ')}
                </div>
            ` : ''}
        </div>
    </div>
    ` : ''}

    ${Object.keys(endOfLife).length > 0 ? `
    <div class="section">
        <h2>End of Life Guidelines</h2>
        <div class="info-grid">
            ${endOfLife.reuse ? `<div class="info-item"><strong>Reuse:</strong><br>${endOfLife.reuse}</div>` : ''}
            ${endOfLife.recycle ? `<div class="info-item"><strong>Recycle:</strong><br>${endOfLife.recycle}</div>` : ''}
            ${endOfLife.contact ? `<div class="info-item"><strong>Contact:</strong><br>${endOfLife.contact}</div>` : ''}
        </div>
    </div>
    ` : ''}

    <div class="footer">
        <p>Digital Product Passport • Generated on ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}</p>
        <p>This document contains public information only. For detailed supply chain and compliance information, please contact the brand directly.</p>
    </div>
</body>
</html>
    `.trim();
  }
}
