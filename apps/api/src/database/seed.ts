import { NestFactory } from "@nestjs/core";
import { AppModule } from "../app.module";
import { SeedService } from "./services/seed.service";

async function bootstrap() {
  const app = await NestFactory.createApplicationContext(AppModule);
  const seedService = app.get(SeedService);

  try {
    console.log("Starting database seeding...");
    await seedService.seedData();
    console.log("Database seeding completed successfully!");
  } catch (error) {
    console.error("Database seeding failed:", error);
    process.exit(1);
  } finally {
    await app.close();
  }
}

bootstrap();