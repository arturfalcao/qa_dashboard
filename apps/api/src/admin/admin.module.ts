import { Module } from "@nestjs/common";
import { TypeOrmModule } from "@nestjs/typeorm";

import { AdminService } from "./admin.service";
import { AdminController } from "./admin.controller";
import { User } from "../database/entities/user.entity";
import { Role } from "../database/entities/role.entity";
import { UserRole } from "../database/entities/user-role.entity";
import { RolesGuard } from "../auth/roles.guard";

@Module({
  imports: [TypeOrmModule.forFeature([User, Role, UserRole])],
  controllers: [AdminController],
  providers: [AdminService, RolesGuard],
})
export class AdminModule {}