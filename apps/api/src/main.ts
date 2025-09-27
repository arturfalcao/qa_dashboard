import { NestFactory } from "@nestjs/core";
import { ValidationPipe } from "@nestjs/common";
import { SwaggerModule, DocumentBuilder } from "@nestjs/swagger";
import { AppModule } from "./app.module";

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.enableCors({
    origin: process.env.FRONTEND_URL
      ? process.env.FRONTEND_URL.split(',')
      : [
          "http://localhost:3000",
          "http://localhost:3002",
          "https://app.packpolish.com",
          "https://operator.packpolish.com"
        ],
    credentials: true,
  });

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );

  const config = new DocumentBuilder()
    .setTitle("Pack and Polish QC Dashboard API")
    .setDescription(
      "AI-driven textile quality control API for 'Made in Portugal' brands",
    )
    .setVersion("1.0")
    .addBearerAuth()
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup("docs", app, document);

  app.getHttpAdapter().get("/docs-json", (req, res) => {
    res.json(document);
  });

  const port = process.env.PORT ? Number(process.env.PORT) : 3001;

  const server = await app.listen(port);
  console.log(`API Server running on http://localhost:${port}`);
  console.log(`API Docs available at http://localhost:${port}/docs`);

  const gracefulShutdown = async (signal: string) => {
    console.log(`Received ${signal}, closing Nest application...`);
    try {
      await app.close();

      if (typeof (server as any).closeAllConnections === "function") {
        (server as any).closeAllConnections();
      }

      await new Promise<void>((resolve) => {
        server.close(() => resolve());
        setTimeout(() => resolve(), 2000);
      });
    } catch (error) {
      console.error("Error during shutdown", error);
    } finally {
      process.exit(0);
    }
  };

  ["SIGINT", "SIGTERM", "SIGQUIT"].forEach((signal) => {
    process.on(signal as NodeJS.Signals, () => gracefulShutdown(signal));
  });
}

bootstrap();
