import { DataSourceOptions } from "typeorm";
import { config as loadEnv } from "dotenv";
import { join } from "path";

const envPaths = [
  join(__dirname, "../../.env"),
  join(__dirname, "../../../.env"),
  join(process.cwd(), "apps/api/.env"),
];

for (const path of envPaths) {
  loadEnv({ path, override: false });
}

const entities = [join(__dirname, "**/*.entity{.ts,.js}")];

const migrations = [join(__dirname, "migrations/*{.ts,.js}")];

const sslConfig = process.env.NODE_ENV === "production" || process.env.DB_SSLMODE === "require"
  ? { rejectUnauthorized: false }
  : false;

export const dataSourceOptions: DataSourceOptions = {
  type: "postgres",
  url: process.env.DATABASE_URL,
  synchronize: false,
  logging: process.env.NODE_ENV === "development",
  entities,
  migrations,
  ssl: sslConfig,
  extra: {
    ssl: sslConfig,
  },
};

export default dataSourceOptions;
