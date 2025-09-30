import { Module } from "@nestjs/common";
import { TypeOrmModule } from "@nestjs/typeorm";

import { Tenant } from "./entities/tenant.entity";
import { Client } from "./entities/client.entity";
import { User } from "./entities/user.entity";
import { Role } from "./entities/role.entity";
import { UserRole } from "./entities/user-role.entity";
import { Factory } from "./entities/factory.entity";
import { DefectType } from "./entities/defect-type.entity";
import { Lot } from "./entities/lot.entity";
import { LotFactory } from "./entities/lot-factory.entity";
import { Inspection } from "./entities/inspection.entity";
import { Defect } from "./entities/defect.entity";
import { Photo } from "./entities/photo.entity";
import { Approval } from "./entities/approval.entity";
import { Report } from "./entities/report.entity";
import { Activity } from "./entities/activity.entity";
import { AuditLog } from "./entities/audit-log.entity";
import { Event } from "./entities/event.entity";
import { Notification } from "./entities/notification.entity";
import { SupplyChainRole } from "./entities/supply-chain-role.entity";
import { FactoryRole } from "./entities/factory-role.entity";
import { LotFactoryRole } from "./entities/lot-factory-role.entity";
import { FactoryCertification } from "./entities/factory-certification.entity";
import { Dpp } from "./entities/dpp.entity";
import { DppEvent } from "./entities/dpp-event.entity";
import { DppAccessLog } from "./entities/dpp-access-log.entity";
import { LotUserAssignment } from "./entities/lot-user-assignment.entity";
import { EdgeDevice } from "./entities/edge-device.entity";
import { InspectionSession } from "./entities/inspection-session.entity";
import { ApparelPiece } from "./entities/apparel-piece.entity";
import { PiecePhoto } from "./entities/piece-photo.entity";
import { PieceDefect } from "./entities/piece-defect.entity";

import { InspectionService } from "./services/inspection.service";
import { LotService } from "./services/lot.service";
import { AnalyticsService } from "./services/analytics.service";
import { EventService } from "./services/event.service";
import { SeedService } from "./services/seed.service";
import { ClientService } from "./services/client.service";
import { TenantService } from "./services/tenant.service";
import { FactoryService } from "./services/factory.service";
import { DefectService } from "./services/defect.service";
import { SupplyChainService } from "./services/supply-chain.service";
import { UserService } from "./services/user.service";
import { EdgeDeviceService } from "./services/edge-device.service";
import { InspectionSessionService } from "./services/inspection-session.service";
import { ApparelPieceService } from "./services/apparel-piece.service";
import { PiecePhotoService } from "./services/piece-photo.service";
import { PieceDefectService } from "./services/piece-defect.service";

import { InspectionController } from "./controllers/inspection.controller";
import { LotController } from "./controllers/lot.controller";
import { AnalyticsController } from "./controllers/analytics.controller";
import { EventController } from "./controllers/event.controller";
import { AdminController } from "./controllers/admin.controller";
import { ClientController } from "./controllers/client.controller";
import { TenantController } from "./controllers/tenant.controller";
import { FactoryController } from "./controllers/factory.controller";
import { SupplyChainController } from "./controllers/supply-chain.controller";
import { UserController } from "./controllers/user.controller";
import { EdgeController } from "./controllers/edge.controller";
import { OperatorController } from "./controllers/operator.controller";
import { DashboardController } from "./controllers/dashboard.controller";
import { SuperAdminController } from "./controllers/super-admin.controller";
import { ESGReportsController } from "./controllers/esg-reports.controller";
import { InspectionSessionController } from "./controllers/inspection-session.controller";
import { StorageModule } from "../storage/storage.module";
import { DppModule } from "../dpp/dpp.module";
import { DppService } from "../dpp/dpp.service";

@Module({
  imports: [
    TypeOrmModule.forFeature([
      Tenant,
      Client,
      User,
      Role,
      UserRole,
      Factory,
      DefectType,
      Lot,
      LotFactory,
      SupplyChainRole,
      FactoryRole,
      FactoryCertification,
      LotFactoryRole,
      LotUserAssignment,
      Inspection,
      Defect,
      Photo,
      Approval,
      Report,
      Activity,
      AuditLog,
      Event,
      Notification,
      Dpp,
      DppEvent,
      DppAccessLog,
      EdgeDevice,
      InspectionSession,
      ApparelPiece,
      PiecePhoto,
      PieceDefect,
    ]),
    StorageModule,
    DppModule,
  ],
  providers: [
    InspectionService,
    LotService,
    AnalyticsService,
    EventService,
    SeedService,
    ClientService,
    TenantService,
    UserService,
    FactoryService,
    DefectService,
    SupplyChainService,
    DppService,
    EdgeDeviceService,
    InspectionSessionService,
    ApparelPieceService,
    PiecePhotoService,
    PieceDefectService,
  ],
  controllers: [
    InspectionController,
    LotController,
    AnalyticsController,
    EventController,
    AdminController,
    ClientController,
    TenantController,
    FactoryController,
    SupplyChainController,
    UserController,
    EdgeController,
    OperatorController,
    DashboardController,
    SuperAdminController,
    ESGReportsController,
    InspectionSessionController,
  ],
  exports: [
    InspectionService,
    LotService,
    AnalyticsService,
    EventService,
    SeedService,
    ClientService,
    TenantService,
    FactoryService,
    DefectService,
    SupplyChainService,
    UserService,
    DppModule,
    TypeOrmModule,
  ],
})
export class DatabaseModule {}
