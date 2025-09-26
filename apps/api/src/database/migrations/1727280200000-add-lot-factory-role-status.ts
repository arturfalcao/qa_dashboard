import { MigrationInterface, QueryRunner } from "typeorm";

export class AddLotFactoryRoleStatus1727280200000 implements MigrationInterface {
  name = "AddLotFactoryRoleStatus1727280200000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`ALTER TABLE lot_factory_roles ADD COLUMN status text NOT NULL DEFAULT 'NOT_STARTED';`);
    await queryRunner.query(`ALTER TABLE lot_factory_roles ADD COLUMN started_at timestamptz;`);
    await queryRunner.query(`ALTER TABLE lot_factory_roles ADD COLUMN completed_at timestamptz;`);

    await queryRunner.query(
      `UPDATE lot_factory_roles
       SET status = 'IN_PROGRESS', started_at = now()
       WHERE id IN (
         SELECT id FROM (
           SELECT lfr.id,
                  ROW_NUMBER() OVER (
                    PARTITION BY lf.lot_id
                    ORDER BY lf.sequence ASC, lfr.sequence ASC
                  ) AS rn
           FROM lot_factory_roles lfr
           JOIN lot_factories lf ON lf.id = lfr.lot_factory_id
         ) ranked
         WHERE ranked.rn = 1
       );`,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`ALTER TABLE lot_factory_roles DROP COLUMN completed_at;`);
    await queryRunner.query(`ALTER TABLE lot_factory_roles DROP COLUMN started_at;`);
    await queryRunner.query(`ALTER TABLE lot_factory_roles DROP COLUMN status;`);
  }
}
