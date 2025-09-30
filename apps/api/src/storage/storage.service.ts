import { Injectable } from "@nestjs/common";
import * as Minio from "minio";
import * as path from "path";

@Injectable()
export class StorageService {
  private minioClient: Minio.Client;
  private photosBucket: string;
  private reportsBucket: string;

  constructor() {
    this.photosBucket = process.env.MINIO_PHOTOS_BUCKET || "pp-photos";
    this.reportsBucket = process.env.MINIO_REPORTS_BUCKET || "pp-reports";

    // Strip protocol from endpoint if present (DigitalOcean Spaces compatibility)
    const rawEndpoint = process.env.MINIO_ENDPOINT || "localhost";
    const endPoint = rawEndpoint.replace(/^https?:\/\//, "");

    this.minioClient = new Minio.Client({
      endPoint,
      port: parseInt(process.env.MINIO_PORT || "9000"),
      useSSL: process.env.MINIO_USE_SSL === "true",
      accessKey: process.env.MINIO_ACCESS_KEY || "minio",
      secretKey: process.env.MINIO_SECRET_KEY || "minio123",
    });
    void this.ensureBuckets();
  }

  private async ensureBuckets() {
    for (const bucket of [this.photosBucket, this.reportsBucket]) {
      try {
        const exists = await this.minioClient.bucketExists(bucket);
        if (!exists) {
          await this.minioClient.makeBucket(bucket, "us-east-1");
        }
      } catch (error) {
        console.error(
          `[StorageService] Unable to ensure bucket ${bucket}`,
          error,
        );
      }
    }
  }

  async getPresignedUploadUrl(
    tenantId: string,
    bucket: "photos" | "reports" = "photos",
  ): Promise<{ uploadUrl: string; key: string }> {
    const targetBucket = this.getBucket(bucket);
    const key = this.generateKey(tenantId, undefined, bucket);
    const uploadUrl = await this.minioClient.presignedPutObject(
      targetBucket,
      key,
      60 * 10,
    ); // 10 minutes

    return { uploadUrl, key };
  }

  async getPresignedDownloadUrl(
    key: string,
    bucket: "photos" | "reports" = "photos",
  ): Promise<string> {
    const targetBucket = this.getBucket(bucket);
    return await this.minioClient.presignedGetObject(
      targetBucket,
      key,
      60 * 10,
    ); // 10 minutes
  }

  async getFileBuffer(
    key: string,
    bucket: "photos" | "reports" = "photos",
  ): Promise<Buffer> {
    const targetBucket = this.getBucket(bucket);
    const stream = await this.minioClient.getObject(targetBucket, key);

    const chunks: Buffer[] = [];
    return new Promise((resolve, reject) => {
      stream.on('data', (chunk) => chunks.push(chunk));
      stream.on('end', () => resolve(Buffer.concat(chunks)));
      stream.on('error', reject);
    });
  }

  async uploadFile(
    buffer: Buffer,
    filename: string,
    contentType = "image/jpeg",
    tenantId?: string,
    bucket: "photos" | "reports" = "photos",
  ): Promise<string> {
    const key = this.generateKey(tenantId || "public", filename, bucket);
    const targetBucket = this.getBucket(bucket);

    await this.minioClient.putObject(targetBucket, key, buffer, buffer.length, {
      "Content-Type": contentType,
    });

    return key;
  }

  async uploadFileWithKey(
    key: string,
    buffer: Buffer,
    contentType = "image/jpeg",
    bucket: "photos" | "reports" = "photos",
  ): Promise<void> {
    const targetBucket = this.getBucket(bucket);
    await this.minioClient.putObject(targetBucket, key, buffer, buffer.length, {
      "Content-Type": contentType,
    });
  }

  async deleteFile(
    key: string,
    bucket: "photos" | "reports" = "photos",
  ): Promise<void> {
    const targetBucket = this.getBucket(bucket);
    try {
      await this.minioClient.removeObject(targetBucket, key);
    } catch (error) {
      console.error("Error deleting file:", error);
    }
  }

  generateKey(
    tenantId: string,
    filename?: string,
    bucket: "photos" | "reports" = "photos",
  ): string {
    if (filename) {
      const ext = path.extname(filename) || ".jpg";
      const baseName = path
        .basename(filename, ext)
        .replace(/[^a-zA-Z0-9-_]/g, "_");
      const prefix = bucket === "reports" ? "reports" : "images";
      return `clients/${tenantId}/${prefix}/${this.generateUUID()}-${baseName}${ext}`;
    }

    const prefix = bucket === "reports" ? "reports" : "images";
    return `clients/${tenantId}/${prefix}/${this.generateUUID()}.jpg`;
  }

  private getBucket(type: "photos" | "reports"): string {
    return type === "reports" ? this.reportsBucket : this.photosBucket;
  }

  private generateUUID(): string {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
      /[xy]/g,
      function (c) {
        const r = (Math.random() * 16) | 0;
        const v = c == "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      },
    );
  }
}
