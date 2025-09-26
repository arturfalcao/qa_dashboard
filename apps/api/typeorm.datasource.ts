import 'reflect-metadata';
import { DataSource } from 'typeorm';
import dataSourceOptions from './src/database/typeorm.config';

export default new DataSource(dataSourceOptions);
