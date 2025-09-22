import {
  Injectable,
  CanActivate,
  ExecutionContext,
  ForbiddenException,
} from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { User } from "../database/entities/user.entity";

@Injectable()
export class TenantGuard implements CanActivate {
  constructor(
    @InjectRepository(User)
    private userRepository: Repository<User>,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = request.user;

    if (!user || !user.tenantId) {
      throw new ForbiddenException("Invalid tenant access");
    }

    const tenantSlug = request.params.tenantSlug || request.query.tenantSlug;
    if (tenantSlug) {
      const userRecord = await this.userRepository.findOne({
        where: { id: user.userId },
        relations: ["tenant"],
      });

      if (!userRecord || userRecord.tenant.slug !== tenantSlug) {
        throw new ForbiddenException("Tenant mismatch");
      }
    }

    request.tenantId = user.tenantId;
    return true;
  }
}
