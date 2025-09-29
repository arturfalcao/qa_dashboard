import { Controller, Post, Body } from "@nestjs/common";
import { ApiTags, ApiOperation } from "@nestjs/swagger";
import { ExportsService } from "./exports.service";
import { ClientId } from "../common/decorators";
import { ExportQuery, ExportQuerySchema } from "@qa-dashboard/shared";
import { ZodValidationPipe } from "../common/zod-validation.pipe";

@ApiTags("exports")
@Controller("exports")
export class ExportsController {
  constructor(private exportsService: ExportsService) {}

  @Post("pdf")
  @ApiOperation({ summary: "Generate PDF report" })
  async generatePDF(
    @ClientId() tenantId: string,
    @Body(new ZodValidationPipe(ExportQuerySchema)) query: ExportQuery,
  ): Promise<{ downloadUrl: string }> {
    const downloadUrl = await this.exportsService.generatePDF(
      tenantId,
      query.lotId,
      query.range,
    );

    return { downloadUrl };
  }

  @Post("csv")
  @ApiOperation({ summary: "Generate CSV export" })
  async generateCSV(
    @ClientId() tenantId: string,
    @Body(new ZodValidationPipe(ExportQuerySchema)) query: ExportQuery,
  ): Promise<{ downloadUrl: string }> {
    const downloadUrl = await this.exportsService.generateCSV(
      tenantId,
      query.range,
    );
    return { downloadUrl };
  }
}
