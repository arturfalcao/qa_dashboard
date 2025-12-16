import {
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Body,
  Param,
  Query,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  ParseUUIDPipe,
  HttpCode,
  HttpStatus,
} from "@nestjs/common";
import { FileInterceptor } from "@nestjs/platform-express";
import { JwtAuthGuard } from "../auth/jwt-auth.guard";
import { TenantId } from "../common/decorators";
import { TechPackCrudService } from "./tech-pack-crud.service";
import { TechPackService } from "./tech-pack.service";

export class CreateTechPackDto {
  styleRef: string;
  productName?: string;
  season?: string;
  designer?: string;
  sampleSize?: string;
  sizeRange?: string[];
}

export class UpdateTechPackDto {
  styleRef?: string;
  productName?: string;
  season?: string;
  designer?: string;
  sampleSize?: string;
  sizeRange?: string[];
  materialComposition?: any[];
  colorways?: any[];
  sizeSpecifications?: any[];
  measurementTolerances?: Record<string, number>;
  constructionDetails?: any[];
  artwork?: any[];
  fabricMap?: any[];
  labels?: any[];
  hangTags?: any[];
  packaging?: any[];
  foldingInstructions?: any[];
  careInstructions?: any[];
  billOfMaterials?: any[];
}

@Controller("tech-packs")
@UseGuards(JwtAuthGuard)
export class TechPackController {
  constructor(
    private readonly techPackCrudService: TechPackCrudService,
    private readonly techPackService: TechPackService,
  ) {}

  @Get()
  async findAll(
    @TenantId() tenantId: string,
    @Query("status") status?: string,
    @Query("search") search?: string,
    @Query("page") page?: string,
    @Query("limit") limit?: string,
  ) {
    return this.techPackCrudService.findAll(tenantId, {
      status: status as any,
      search,
      page: page ? parseInt(page, 10) : 1,
      limit: limit ? parseInt(limit, 10) : 20,
    });
  }

  @Get(":id")
  async findOne(
    @TenantId() tenantId: string,
    @Param("id", ParseUUIDPipe) id: string,
  ) {
    return this.techPackCrudService.findOne(tenantId, id);
  }

  @Post()
  async create(
    @TenantId() tenantId: string,
    @Body() dto: CreateTechPackDto,
  ) {
    return this.techPackCrudService.create(tenantId, dto);
  }

  @Put(":id")
  async update(
    @TenantId() tenantId: string,
    @Param("id", ParseUUIDPipe) id: string,
    @Body() dto: UpdateTechPackDto,
  ) {
    return this.techPackCrudService.update(tenantId, id, dto);
  }

  @Delete(":id")
  @HttpCode(HttpStatus.NO_CONTENT)
  async delete(
    @TenantId() tenantId: string,
    @Param("id", ParseUUIDPipe) id: string,
  ) {
    return this.techPackCrudService.delete(tenantId, id);
  }

  @Post("upload")
  @UseInterceptors(FileInterceptor("file"))
  async uploadAndExtract(
    @TenantId() tenantId: string,
    @UploadedFile() file: Express.Multer.File,
    @Body("styleRef") styleRef?: string,
  ) {
    return this.techPackCrudService.uploadAndProcess(tenantId, file, styleRef);
  }

  @Post(":id/reprocess")
  async reprocess(
    @TenantId() tenantId: string,
    @Param("id", ParseUUIDPipe) id: string,
  ) {
    return this.techPackCrudService.reprocess(tenantId, id);
  }

  @Get(":id/lots")
  async getLots(
    @TenantId() tenantId: string,
    @Param("id", ParseUUIDPipe) id: string,
  ) {
    return this.techPackCrudService.getLotsUsingTechPack(tenantId, id);
  }
}
