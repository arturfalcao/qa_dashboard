import { Injectable } from '@nestjs/common';
import * as Minio from 'minio';

@Injectable()
export class StorageService {
  private minioClient: Minio.Client;
  private bucketName: string;

  constructor() {
    this.bucketName = process.env.MINIO_BUCKET || 'qc-images';
    this.minioClient = new Minio.Client({
      endPoint: process.env.MINIO_ENDPOINT || 'localhost',
      port: parseInt(process.env.MINIO_PORT || '9000'),
      useSSL: process.env.MINIO_USE_SSL === 'true',
      accessKey: process.env.MINIO_ACCESS_KEY || 'minioadmin',
      secretKey: process.env.MINIO_SECRET_KEY || 'minioadmin123',
    });
  }

  async getPresignedUploadUrl(tenantId: string): Promise<{ uploadUrl: string; key: string }> {
    const key = `tenants/${tenantId}/images/${this.generateUUID()}.jpg`;
    const uploadUrl = await this.minioClient.presignedPutObject(this.bucketName, key, 60 * 10); // 10 minutes
    
    return { uploadUrl, key };
  }

  async getPresignedDownloadUrl(key: string): Promise<string> {
    return await this.minioClient.presignedGetObject(this.bucketName, key, 60 * 10); // 10 minutes
  }

  async getPresignedUrl(key: string, expiry: number = 600): Promise<string> {
    return await this.minioClient.presignedGetObject(this.bucketName, key, expiry);
  }

  async uploadFile(buffer: Buffer, filename: string, contentType = 'image/jpeg', tenantId?: string): Promise<string> {
    const key = tenantId
      ? `tenants/${tenantId}/images/${this.generateUUID()}-${filename}`
      : `images/${this.generateUUID()}-${filename}`;

    await this.minioClient.putObject(this.bucketName, key, buffer, buffer.length, {
      'Content-Type': contentType,
    });

    return key;
  }

  async uploadFileWithKey(key: string, buffer: Buffer, contentType = 'image/jpeg'): Promise<void> {
    await this.minioClient.putObject(this.bucketName, key, buffer, buffer.length, {
      'Content-Type': contentType,
    });
  }

  async deleteFile(key: string): Promise<void> {
    try {
      await this.minioClient.removeObject(this.bucketName, key);
    } catch (error) {
      console.error('Error deleting file:', error);
    }
  }

  generateKey(tenantId: string, filename?: string): string {
    return `tenants/${tenantId}/images/${filename || this.generateUUID()}.jpg`;
  }

  private generateUUID(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}