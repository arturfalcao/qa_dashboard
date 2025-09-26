import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { Event } from "../entities/event.entity";
import { EventType } from "@qa-dashboard/shared";

@Injectable()
export class EventService {
  constructor(
    @InjectRepository(Event)
    private eventRepository: Repository<Event>,
  ) {}

  async getEvents(
    clientId: string,
    since?: string,
    limit = 100,
  ): Promise<Event[]> {
    const query = this.eventRepository
      .createQueryBuilder("event")
      .where("event.clientId = :clientId", { clientId })
      .orderBy("event.createdAt", "DESC")
      .limit(limit);

    if (since) {
      query.andWhere("event.createdAt > :since", { since: new Date(since) });
    }

    return await query.getMany();
  }

  async createEvent(
    clientId: string,
    type: EventType,
    payload: Record<string, unknown>,
    lotId?: string,
  ): Promise<Event> {
    const event = this.eventRepository.create({
      clientId,
      lotId,
      type,
      payload,
    });

    return await this.eventRepository.save(event);
  }
}
