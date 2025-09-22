import {
  Controller,
  Get,
  Post,
  Delete,
  Body,
  Param,
  Query,
  UseGuards,
  HttpCode,
  HttpStatus,
  UploadedFile,
  UseInterceptors,
} from "@nestjs/common";
import { FileInterceptor } from "@nestjs/platform-express";
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiConsumes,
} from "@nestjs/swagger";
import { JwtAuthGuard } from "../../auth/jwt-auth.guard";
import { TenantGuard } from "../../auth/tenant.guard";
import { CurrentTenant, TenantId, Public } from "../../common/decorators";
import { ZodValidationPipe } from "../../common/zod-validation.pipe";
import {
  InspectionPhotoService,
  CreateInspectionPhotoDto,
} from "../services/inspection-photo.service";
import { StorageService } from "../../storage/storage.service";
import { z } from "zod";
import { PhotoAngle } from "@qa-dashboard/shared";

const CreatePhotoSchema = z.object({
  inspectionId: z.string().uuid(),
  angle: z.nativeEnum(PhotoAngle),
  capturedAt: z.string().datetime().optional(),
});

const GetPhotosByAngleSchema = z.object({
  angle: z.nativeEnum(PhotoAngle),
});

@ApiTags("Inspection Photos")
@Controller("inspection-photos")
@UseGuards(JwtAuthGuard)
export class InspectionPhotoController {
  constructor(
    private inspectionPhotoService: InspectionPhotoService,
    private storageService: StorageService,
  ) {}

  @Post("upload")
  @Public()
  @ApiOperation({ summary: "Upload a new inspection photo" })
  @ApiConsumes("multipart/form-data")
  @ApiResponse({ status: 201, description: "Photo uploaded successfully" })
  @UseInterceptors(FileInterceptor("photo"))
  async uploadPhoto(
    @TenantId() tenantId: string,
    @UploadedFile() file: any,
    @Body(new ZodValidationPipe(CreatePhotoSchema))
    createDto: z.infer<typeof CreatePhotoSchema>,
  ) {
    if (!file) {
      throw new Error("No file uploaded");
    }

    const finalTenantId = tenantId || "045f1210-98cc-457e-9d44-982a1875527d";
    // Upload file to storage
    const photoKey = await this.storageService.uploadFile(
      file.buffer,
      file.originalname,
      file.mimetype,
      finalTenantId,
    );

    const photoDto: CreateInspectionPhotoDto = {
      inspectionId: createDto.inspectionId,
      angle: createDto.angle,
      photoKey,
      capturedAt: createDto.capturedAt
        ? new Date(createDto.capturedAt)
        : undefined,
    };

    return await this.inspectionPhotoService.createPhoto(
      finalTenantId,
      photoDto,
    );
  }

  @Get("inspection/:inspectionId")
  @Public()
  @ApiOperation({ summary: "Get all photos for an inspection" })
  @ApiResponse({ status: 200, description: "Photos retrieved successfully" })
  async getPhotosForInspection(
    @TenantId() tenantId: string,
    @Param("inspectionId") inspectionId: string,
  ) {
    const finalTenantId = tenantId || "045f1210-98cc-457e-9d44-982a1875527d";
    return await this.inspectionPhotoService.getPhotosForInspection(
      finalTenantId,
      inspectionId,
    );
  }

  @Get("inspection/:inspectionId/angle")
  @Public()
  @ApiOperation({ summary: "Get photos for an inspection by angle" })
  @ApiResponse({ status: 200, description: "Photos retrieved successfully" })
  async getPhotosByAngle(
    @TenantId() tenantId: string,
    @Param("inspectionId") inspectionId: string,
    @Query(new ZodValidationPipe(GetPhotosByAngleSchema))
    query: z.infer<typeof GetPhotosByAngleSchema>,
  ) {
    const finalTenantId = tenantId || "045f1210-98cc-457e-9d44-982a1875527d";
    return await this.inspectionPhotoService.getPhotosByAngle(
      finalTenantId,
      inspectionId,
      query.angle,
    );
  }

  @Get(":id")
  @Public()
  @ApiOperation({ summary: "Get photo by ID" })
  @ApiResponse({ status: 200, description: "Photo retrieved successfully" })
  async getPhotoById(
    @TenantId() tenantId: string,
    @Param("id") photoId: string,
  ) {
    const finalTenantId = tenantId || "045f1210-98cc-457e-9d44-982a1875527d";
    const photo = await this.inspectionPhotoService.getPhotoById(
      finalTenantId,
      photoId,
    );
    if (!photo) {
      throw new Error("Photo not found");
    }
    return photo;
  }

  @Delete(":id")
  @Public()
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: "Delete a photo" })
  @ApiResponse({ status: 204, description: "Photo deleted successfully" })
  async deletePhoto(
    @TenantId() tenantId: string,
    @Param("id") photoId: string,
  ) {
    const finalTenantId = tenantId || "045f1210-98cc-457e-9d44-982a1875527d";
    await this.inspectionPhotoService.deletePhoto(finalTenantId, photoId);
  }

  @Get("inspection/:inspectionId/download-url")
  @Public()
  @ApiOperation({ summary: "Get presigned URL for photo download" })
  @ApiResponse({
    status: 200,
    description: "Download URL generated successfully",
  })
  async getPhotoDownloadUrl(
    @TenantId() tenantId: string,
    @Param("photoId") photoId: string,
  ) {
    const finalTenantId = tenantId || "045f1210-98cc-457e-9d44-982a1875527d";
    const photo = await this.inspectionPhotoService.getPhotoById(
      finalTenantId,
      photoId,
    );
    if (!photo) {
      throw new Error("Photo not found");
    }

    const downloadUrl = await this.storageService.getPresignedUrl(
      photo.photoKey,
      3600,
    ); // 1 hour expiry
    return { downloadUrl };
  }
}
