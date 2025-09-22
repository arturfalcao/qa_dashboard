import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import * as bcrypt from 'bcryptjs';

import { Tenant } from '../entities/tenant.entity';
import { User } from '../entities/user.entity';
import { Vendor } from '../entities/vendor.entity';
import { Style } from '../entities/style.entity';
import { Batch } from '../entities/batch.entity';
import { Garment } from '../entities/garment.entity';
import { UserRole, BatchStatus } from '@qa-dashboard/shared';

@Injectable()
export class SeedService {
  constructor(
    @InjectRepository(Tenant)
    private tenantRepository: Repository<Tenant>,
    @InjectRepository(User)
    private userRepository: Repository<User>,
    @InjectRepository(Vendor)
    private vendorRepository: Repository<Vendor>,
    @InjectRepository(Style)
    private styleRepository: Repository<Style>,
    @InjectRepository(Batch)
    private batchRepository: Repository<Batch>,
    @InjectRepository(Garment)
    private garmentRepository: Repository<Garment>,
  ) {}

  async seedData(): Promise<void> {
    console.log('Starting seed process...');

    // Create tenants
    const tenant1 = await this.createTenant('Hey Marly', 'heymarly');
    const tenant2 = await this.createTenant('Sample Brand', 'samplebrand');

    // Create users for each tenant
    await this.createUsers(tenant1.id);
    await this.createUsers(tenant2.id);

    // Create vendors and styles for each tenant
    await this.createVendorsAndStyles(tenant1.id);
    await this.createVendorsAndStyles(tenant2.id);

    console.log('Seed completed successfully!');
  }

  private async createTenant(name: string, slug: string): Promise<Tenant> {
    const existingTenant = await this.tenantRepository.findOne({ where: { slug } });
    if (existingTenant) {
      console.log(`Tenant ${name} already exists`);
      return existingTenant;
    }

    const tenant = this.tenantRepository.create({ name, slug });
    await this.tenantRepository.save(tenant);
    console.log(`Created tenant: ${name}`);
    return tenant;
  }

  private async createUsers(tenantId: string): Promise<void> {
    const tenant = await this.tenantRepository.findOne({ where: { id: tenantId } });
    const domain = tenant.slug === 'heymarly' ? 'marly.example' : 'brand.example';

    const users = [
      {
        email: `admin@${domain}`,
        password: 'demo1234',
        role: UserRole.CLIENT_ADMIN,
      },
      {
        email: `viewer@${domain}`,
        password: 'demo1234',
        role: UserRole.CLIENT_VIEWER,
      },
    ];

    for (const userData of users) {
      const existingUser = await this.userRepository.findOne({
        where: { email: userData.email, tenantId },
      });

      if (existingUser) {
        console.log(`User ${userData.email} already exists`);
        continue;
      }

      const passwordHash = await bcrypt.hash(userData.password, 10);
      const user = this.userRepository.create({
        tenantId,
        email: userData.email,
        passwordHash,
        role: userData.role,
        isActive: true,
      });

      await this.userRepository.save(user);
      console.log(`Created user: ${userData.email}`);
    }
  }

  private async createVendorsAndStyles(tenantId: string): Promise<void> {
    // Create vendors
    const vendors = [
      { name: 'Premium Textiles Co.', code: 'PTC' },
      { name: 'Global Garments Ltd.', code: 'GGL' },
      { name: 'Fashion Forward Inc.', code: 'FFI' },
    ];

    const createdVendors = [];
    for (const vendorData of vendors) {
      const existingVendor = await this.vendorRepository.findOne({
        where: { code: vendorData.code, tenantId },
      });

      if (existingVendor) {
        createdVendors.push(existingVendor);
        continue;
      }

      const vendor = this.vendorRepository.create({
        tenantId,
        ...vendorData,
      });

      const savedVendor = await this.vendorRepository.save(vendor);
      createdVendors.push(savedVendor);
      console.log(`Created vendor: ${vendorData.name}`);
    }

    // Create styles
    const styles = [
      { styleCode: 'T-001', description: 'Classic Cotton T-Shirt' },
      { styleCode: 'H-002', description: 'Premium Hoodie' },
      { styleCode: 'J-003', description: 'Denim Jacket' },
      { styleCode: 'P-004', description: 'Casual Polo' },
    ];

    const createdStyles = [];
    for (const styleData of styles) {
      const existingStyle = await this.styleRepository.findOne({
        where: { styleCode: styleData.styleCode, tenantId },
      });

      if (existingStyle) {
        createdStyles.push(existingStyle);
        continue;
      }

      const style = this.styleRepository.create({
        tenantId,
        ...styleData,
      });

      const savedStyle = await this.styleRepository.save(style);
      createdStyles.push(savedStyle);
      console.log(`Created style: ${styleData.styleCode}`);
    }

    // Create batches
    await this.createBatches(tenantId, createdVendors, createdStyles);
  }

  private async createBatches(tenantId: string, vendors: Vendor[], styles: Style[]): Promise<void> {
    const batches = [
      {
        poNumber: 'PO-2024-001',
        quantity: 1000,
        status: BatchStatus.IN_PROGRESS,
        vendorId: vendors[0].id,
        styleId: styles[0].id,
      },
      {
        poNumber: 'PO-2024-002',
        quantity: 500,
        status: BatchStatus.IN_PROGRESS,
        vendorId: vendors[1].id,
        styleId: styles[1].id,
      },
      {
        poNumber: 'PO-2024-003',
        quantity: 750,
        status: BatchStatus.AWAITING_APPROVAL,
        vendorId: vendors[2].id,
        styleId: styles[2].id,
      },
    ];

    for (const batchData of batches) {
      const existingBatch = await this.batchRepository.findOne({
        where: { poNumber: batchData.poNumber, tenantId },
      });

      if (existingBatch) {
        console.log(`Batch ${batchData.poNumber} already exists`);
        continue;
      }

      const batch = this.batchRepository.create({
        tenantId,
        ...batchData,
      });

      const savedBatch = await this.batchRepository.save(batch);
      console.log(`Created batch: ${batchData.poNumber}`);

      // Create some garments for each batch
      await this.createGarments(tenantId, savedBatch.id, Math.min(100, batchData.quantity));
    }
  }

  private async createGarments(tenantId: string, batchId: string, count: number): Promise<void> {
    const sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];
    const colors = ['Black', 'White', 'Navy', 'Gray', 'Red', 'Blue'];

    const garments = [];
    for (let i = 1; i <= count; i++) {
      const garment = this.garmentRepository.create({
        tenantId,
        batchId,
        serial: `G${String(i).padStart(4, '0')}`,
        size: sizes[Math.floor(Math.random() * sizes.length)],
        color: colors[Math.floor(Math.random() * colors.length)],
      });
      garments.push(garment);
    }

    await this.garmentRepository.save(garments);
    console.log(`Created ${count} garments for batch`);
  }
}