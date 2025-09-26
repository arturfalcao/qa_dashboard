import { MigrationInterface, QueryRunner, Table, TableForeignKey, TableIndex } from "typeorm";

export class AddLotSuppliers1727280000000 implements MigrationInterface {
  name = "AddLotSuppliers1727280000000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.createTable(
      new Table({
        name: "lot_factories",
        columns: [
          {
            name: "id",
            type: "uuid",
            isPrimary: true,
            generationStrategy: "uuid",
            default: "uuid_generate_v4()",
          },
          {
            name: "lot_id",
            type: "uuid",
            isNullable: false,
          },
          {
            name: "factory_id",
            type: "uuid",
            isNullable: false,
          },
          {
            name: "sequence",
            type: "integer",
            default: 0,
          },
          {
            name: "stage",
            type: "text",
            isNullable: true,
          },
          {
            name: "is_primary",
            type: "boolean",
            default: false,
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
      "lot_factories",
      new TableForeignKey({
        columnNames: ["lot_id"],
        referencedColumnNames: ["id"],
        referencedTableName: "lots",
        onDelete: "CASCADE",
      }),
    );

    await queryRunner.createForeignKey(
      "lot_factories",
      new TableForeignKey({
        columnNames: ["factory_id"],
        referencedColumnNames: ["id"],
        referencedTableName: "factories",
        onDelete: "CASCADE",
      }),
    );

    await queryRunner.createIndex(
      "lot_factories",
      new TableIndex({
        name: "idx_lot_factories_lot_id",
        columnNames: ["lot_id"],
      }),
    );

    await queryRunner.createIndex(
      "lot_factories",
      new TableIndex({
        name: "idx_lot_factories_factory_id",
        columnNames: ["factory_id"],
      }),
    );

    await queryRunner.query(
      `INSERT INTO lot_factories (id, lot_id, factory_id, sequence, is_primary)
       SELECT uuid_generate_v4(), id, factory_id, 0, true
       FROM lots
       WHERE factory_id IS NOT NULL`,
    );

    await queryRunner.createIndex(
      "lot_factories",
      new TableIndex({
        name: "uniq_lot_factories_lot_factory",
        columnNames: ["lot_id", "factory_id"],
        isUnique: true,
      }),
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.dropIndex("lot_factories", "uniq_lot_factories_lot_factory");
    await queryRunner.dropIndex("lot_factories", "idx_lot_factories_factory_id");
    await queryRunner.dropIndex("lot_factories", "idx_lot_factories_lot_id");
    await queryRunner.dropTable("lot_factories");
  }
}
