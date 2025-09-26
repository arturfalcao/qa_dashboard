import { MigrationInterface, QueryRunner, Table, TableForeignKey, TableIndex } from "typeorm";

export class AddFactoryCertifications1758851000000 implements MigrationInterface {
  name = "AddFactoryCertifications1758851000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.createTable(
      new Table({
        name: "factory_certifications",
        columns: [
          {
            name: "id",
            type: "uuid",
            isPrimary: true,
            generationStrategy: "uuid",
            default: "uuid_generate_v4()",
          },
          {
            name: "factory_id",
            type: "uuid",
            isNullable: false,
          },
          {
            name: "certification",
            type: "text",
            isNullable: false,
          },
          {
            name: "created_at",
            type: "timestamptz",
            default: "now()",
          },
          {
            name: "updated_at",
            type: "timestamptz",
            default: "now()",
          },
        ],
      }),
    );

    await queryRunner.createForeignKey(
      "factory_certifications",
      new TableForeignKey({
        columnNames: ["factory_id"],
        referencedColumnNames: ["id"],
        referencedTableName: "factories",
        onDelete: "CASCADE",
      }),
    );

    await queryRunner.createIndex(
      "factory_certifications",
      new TableIndex({
        name: "idx_factory_certifications_factory_id",
        columnNames: ["factory_id"],
      }),
    );

    await queryRunner.createIndex(
      "factory_certifications",
      new TableIndex({
        name: "uniq_factory_certifications_factory_certification",
        columnNames: ["factory_id", "certification"],
        isUnique: true,
      }),
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.dropIndex(
      "factory_certifications",
      "uniq_factory_certifications_factory_certification",
    );
    await queryRunner.dropIndex("factory_certifications", "idx_factory_certifications_factory_id");
    await queryRunner.dropTable("factory_certifications");
  }
}
