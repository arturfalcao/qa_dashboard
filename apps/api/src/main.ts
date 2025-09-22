import { NestFactory } from "@nestjs/core";
import { ValidationPipe } from "@nestjs/common";
import { SwaggerModule, DocumentBuilder } from "@nestjs/swagger";
import { AppModule } from "./app.module";

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.enableCors({
    origin: process.env.FRONTEND_URL || "http://localhost:3000",
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

  await app.listen(3001);
  console.log("API Server running on http://localhost:3001");
  console.log("API Docs available at http://localhost:3001/docs");
}

bootstrap();
