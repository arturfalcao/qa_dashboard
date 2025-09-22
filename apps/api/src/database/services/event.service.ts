import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Event } from '../entities/event.entity';
import { EventType } from '@qa-dashboard/shared';

@Injectable()
export class EventService {
  constructor(
    @InjectRepository(Event)
    private eventRepository: Repository<Event>,
  ) {}

  async getEvents(tenantId: string, since?: string, limit = 100): Promise<Event[]> {
    const query = this.eventRepository
      .createQueryBuilder('event')
      .where('event.tenantId = :tenantId', { tenantId })
      .orderBy('event.createdAt', 'DESC')
      .limit(limit);

    if (since) {
      query.andWhere('event.createdAt > :since', { since: new Date(since) });
    }

    return await query.getMany();
  }

  async createEvent(tenantId: string, type: EventType, payload: any): Promise<Event> {
    const event = this.eventRepository.create({
      tenantId,
      type,
      payload,
    });

    return await this.eventRepository.save(event);
  }
}