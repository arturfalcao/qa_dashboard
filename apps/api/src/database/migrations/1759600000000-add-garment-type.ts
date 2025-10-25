import { MigrationInterface, QueryRunner } from "typeorm";

export class AddGarmentType1759600000000 implements MigrationInterface {
  name = "AddGarmentType1759600000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Create the enum type
    await queryRunner.query(`
      CREATE TYPE "garment_type_enum" AS ENUM (
        'T_SHIRT',
        'POLO_SHIRT',
        'DRESS_SHIRT',
        'BLOUSE',
        'DRESS',
        'SKIRT',
        'PANTS',
        'JEANS',
        'SHORTS',
        'JACKET',
        'COAT',
        'SWEATER',
        'HOODIE',
        'SWEATSHIRT',
        'UNDERWEAR',
        'SOCKS',
        'ACTIVEWEAR',
        'SWIMWEAR',
        'JUMPSUIT',
        'ROMPER',
        'OTHER'
      )
    `);

    // Add garment_type column to lots table
    await queryRunner.query(`
      ALTER TABLE "lots"
      ADD COLUMN "garment_type" "garment_type_enum" NULL
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Drop the column
    await queryRunner.query(`
      ALTER TABLE "lots"
      DROP COLUMN "garment_type"
    `);

    // Drop the enum type
    await queryRunner.query(`
      DROP TYPE "garment_type_enum"
    `);
  }
}
