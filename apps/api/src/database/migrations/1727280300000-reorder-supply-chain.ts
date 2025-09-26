import { MigrationInterface, QueryRunner } from "typeorm";

export class ReorderSupplyChain1727280300000 implements MigrationInterface {
  name = "ReorderSupplyChain1727280300000";

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      UPDATE supply_chain_roles
      SET default_sequence = CASE key
        WHEN 'FIBER_PREP' THEN 10
        WHEN 'FABRIC_DYE_FINISH' THEN 20
        WHEN 'FABRIC_WASH_PREP' THEN 30
        WHEN 'FABRIC_INSPECTION_RELAX' THEN 40
        WHEN 'PATTERN_GRADING' THEN 50
        WHEN 'MARKER_CUTTING' THEN 60
        WHEN 'EMBROIDERY_APPLIQUE_LASER' THEN 70
        WHEN 'BUNDLING_SEWING' THEN 80
        WHEN 'INLINE_QC' THEN 90
        WHEN 'SCREEN_PRINTING' THEN 100
        WHEN 'HEAT_TRANSFER' THEN 110
        WHEN 'SUBLIMATION' THEN 120
        WHEN 'DIGITAL_PRINTING' THEN 130
        WHEN 'TRIMS_EMBELLISH' THEN 140
        WHEN 'GARMENT_WASH_SOFTEN' THEN 150
        WHEN 'FINAL_QA' THEN 160
        WHEN 'IRON_PRESS_DETHREAD' THEN 170
        WHEN 'NEEDLE_METAL_DETECT' THEN 180
        WHEN 'PACK_TAG_BAG' THEN 190
        WHEN 'WAREHOUSE_LOGISTICS' THEN 200
        WHEN 'FABRIC_LAB_TEST' THEN 905
        WHEN 'FUNCTIONAL_COATING' THEN 910
        WHEN 'REGULATORY_CHECKS' THEN 920
        WHEN 'SUSTAINABILITY_TRACK' THEN 930
        WHEN 'DOCUMENTATION_DPP' THEN 940
        ELSE default_sequence
      END;
    `);

    await queryRunner.query(`
      WITH ranked AS (
        SELECT
          lfr.id,
          ROW_NUMBER() OVER (
            PARTITION BY lfr.lot_factory_id
            ORDER BY scr.default_sequence ASC, lfr.sequence ASC
          ) - 1 AS new_sequence
        FROM lot_factory_roles lfr
        JOIN supply_chain_roles scr ON scr.id = lfr.role_id
      )
      UPDATE lot_factory_roles AS target
      SET sequence = ranked.new_sequence
      FROM ranked
      WHERE ranked.id = target.id;
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      UPDATE supply_chain_roles
      SET default_sequence = CASE key
        WHEN 'FIBER_PREP' THEN 0
        WHEN 'FABRIC_DYE_FINISH' THEN 1
        WHEN 'FABRIC_WASH_PREP' THEN 2
        WHEN 'FABRIC_INSPECTION_RELAX' THEN 3
        WHEN 'PATTERN_GRADING' THEN 4
        WHEN 'MARKER_CUTTING' THEN 5
        WHEN 'EMBROIDERY_APPLIQUE_LASER' THEN 6
        WHEN 'BUNDLING_SEWING' THEN 7
        WHEN 'INLINE_QC' THEN 8
        WHEN 'SCREEN_PRINTING' THEN 9
        WHEN 'HEAT_TRANSFER' THEN 10
        WHEN 'SUBLIMATION' THEN 11
        WHEN 'DIGITAL_PRINTING' THEN 12
        WHEN 'TRIMS_EMBELLISH' THEN 13
        WHEN 'GARMENT_WASH_SOFTEN' THEN 14
        WHEN 'FINAL_QA' THEN 15
        WHEN 'IRON_PRESS_DETHREAD' THEN 16
        WHEN 'NEEDLE_METAL_DETECT' THEN 17
        WHEN 'PACK_TAG_BAG' THEN 18
        WHEN 'WAREHOUSE_LOGISTICS' THEN 19
        WHEN 'FABRIC_LAB_TEST' THEN 20
        WHEN 'FUNCTIONAL_COATING' THEN 21
        WHEN 'REGULATORY_CHECKS' THEN 22
        WHEN 'SUSTAINABILITY_TRACK' THEN 23
        WHEN 'DOCUMENTATION_DPP' THEN 24
        ELSE default_sequence
      END;
    `);

    await queryRunner.query(`
      WITH ranked AS (
        SELECT
          lfr.id,
          ROW_NUMBER() OVER (
            PARTITION BY lfr.lot_factory_id
            ORDER BY lfr.sequence ASC
          ) - 1 AS new_sequence
        FROM lot_factory_roles lfr
      )
      UPDATE lot_factory_roles AS target
      SET sequence = ranked.new_sequence
      FROM ranked
      WHERE ranked.id = target.id;
    `);
  }
}
