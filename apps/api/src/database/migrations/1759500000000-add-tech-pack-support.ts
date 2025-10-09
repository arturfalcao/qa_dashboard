import { MigrationInterface, QueryRunner, TableColumn } from "typeorm";

export class AddTechPackSupport1759500000000 implements MigrationInterface {
  name = "AddTechPackSupport1759500000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Add tech pack file URL to lots table
    await queryRunner.addColumn(
      "lots",
      new TableColumn({
        name: "tech_pack_file_key",
        type: "varchar",
        length: "500",
        isNullable: true,
        comment: "Storage key for the uploaded tech pack file",
      })
    );

    // Add tech pack extracted data as JSONB
    await queryRunner.addColumn(
      "lots",
      new TableColumn({
        name: "tech_pack_data",
        type: "jsonb",
        isNullable: true,
        comment: "AI-extracted structured data from tech pack",
      })
    );

    // Add size specifications as a separate JSONB column for easy querying
    await queryRunner.addColumn(
      "lots",
      new TableColumn({
        name: "size_specifications",
        type: "jsonb",
        isNullable: true,
        comment: "Size specifications extracted from tech pack for AI measurement validation",
      })
    );

    // Add tech pack processing status
    await queryRunner.addColumn(
      "lots",
      new TableColumn({
        name: "tech_pack_status",
        type: "varchar",
        length: "50",
        isNullable: true,
        default: null,
        comment: "Status of tech pack processing: pending, processing, completed, failed",
      })
    );

    // Add timestamp for when tech pack was uploaded
    await queryRunner.addColumn(
      "lots",
      new TableColumn({
        name: "tech_pack_uploaded_at",
        type: "timestamp",
        isNullable: true,
        comment: "Timestamp when tech pack was uploaded",
      })
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.dropColumn("lots", "tech_pack_uploaded_at");
    await queryRunner.dropColumn("lots", "tech_pack_status");
    await queryRunner.dropColumn("lots", "size_specifications");
    await queryRunner.dropColumn("lots", "tech_pack_data");
    await queryRunner.dropColumn("lots", "tech_pack_file_key");
  }
}