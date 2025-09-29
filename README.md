# Pack and Polish QC Dashboard - AI-Driven Textile Quality Control

A production-ready multi-tenant SaaS quality control dashboard for 'Made in Portugal' textile brands. Features real-time AI inspection feeds, zero-defect analytics, batch approvals, and ESG reporting capabilities.

*"Guarantee each 'Made in Portugal' piece arrives perfect, with minimal environmental impact"*

## 🚀 Quick Start (One Command)

```bash
docker compose up
```

That's it! After all services start:

1. **Access the dashboard**: http://localhost:3000
2. **API Documentation**: http://localhost:3001/docs
3. **MinIO Console**: http://localhost:9003 (minioadmin/minioadmin123)
   - **MinIO API**: http://localhost:9002

## 🏗️ Architecture

**Frontend**: Next.js 14 with App Router, TypeScript, Tailwind CSS, TanStack Query
**Backend**: NestJS with TypeScript, REST APIs, Zod validation  
**Database**: PostgreSQL 15 with full schema and indexes
**Storage**: MinIO (S3-compatible) for image storage with presigned URLs
**Auth**: JWT (access/refresh tokens) with bcrypt password hashing
**Analytics**: Real-time ESG dashboards with Recharts visualization
**Exports**: Server-side PDF generation (Puppeteer) + CSV exports
**Infrastructure**: Docker Compose with health checks and dependencies
**QC Features**: Computer vision inspection simulation, zero-defect tracking

## 📊 Features

### Live Inspection Feed
- Real-time AI inspection updates every 5 seconds
- Industrial camera photo evidence (before/after images)
- Instant defect rejection with event banners
- Live approval dashboard with lot-by-lot status
- Infinite scroll with filtering

### Zero-Defect Management
- Batch overview with progress tracking
- Detailed batch views with audit logs
- Approval/rejection workflow (admin only)
- Pay-per-piece tracking (≈ €0.90/piece)
- Status tracking and notifications

### ESG Analytics Dashboard
- Real-time defect rate analysis by vendor/style
- Sustainability metrics and environmental impact
- Defect type breakdown with computer vision insights
- Approval time analytics (avg, p50, p90)
- Interactive ESG dashboards with filters

### Professional Exports
- PDF reports with KPIs, charts, and ESG metrics
- CSV data exports with full inspection details
- API integration ready for client ERPs
- Batch-specific or time-range exports

### AI Inspection Simulator
- Simulates computer vision inspection continuously
- 6-8% defect rate matching real-world performance
- Automatic batch progression to awaiting approval
- Sample images with AI-detected defects
- Start/stop controls in sidebar

## 👤 Demo Credentials

### Portuguese Brand A (heymarly)
- **Admin**: admin@marly.example / demo1234
- **Viewer**: viewer@marly.example / demo1234

### Portuguese Brand B (samplebrand)  
- **Admin**: admin@brand.example / demo1234
- **Viewer**: viewer@brand.example / demo1234

**Roles**:
- `client_admin`: Full access including batch approval/rejection
- `client_viewer`: Read-only access to all data

## 🎯 Demo Script (5-7 minutes)

1. **Login & Setup** (1 min)
   - Go to http://localhost:3000
   - Login with admin@marly.example / demo1234
   - Seed database: POST http://localhost:3001/admin/seed

2. **Start Mock Generator** (30 sec)  
   - Click "Start Mock Data" in sidebar
   - Watch live feed populate with inspections

3. **Live Feed** (1 min)
   - View real-time inspection cards
   - Notice defect detection event banners
   - See photo evidence and garment details

4. **Batch Management** (2 min)
   - Navigate to Batches page
   - Filter by status (awaiting approval)
   - Click into batch detail
   - Review inspection progress and metrics
   - Approve or reject batch with comments

5. **Analytics** (2 min)
   - View defect rate KPIs
   - Explore throughput trends
   - Analyze defect type breakdown
   - Switch time ranges and groupings

6. **Exports** (1 min)
   - Generate PDF report
   - Export CSV data
   - Download files via presigned URLs

## 🤝 Paco Interoperability Briefing

Preparing for a partner session with Paco? Review the dedicated [Paco Interoperability Playbook](docs/paco_interoperability.md) for a narrative walkthrough, demo script, and configuration checklist that prove how Paco can onboard their own brand clients and share live QA evidence with end customers.

## 🔧 Technical Details

### Database Schema
```sql
-- Key tables with tenant isolation
tenants (id, name, slug)
users (id, tenant_id, email, role, password_hash)
vendors (id, tenant_id, name, code)
styles (id, tenant_id, style_code, description)  
batches (id, tenant_id, vendor_id, style_id, po_number, quantity, status)
garments (id, tenant_id, batch_id, serial, size, color)
inspections (id, tenant_id, garment_id, has_defect, defect_type, notes, photo_keys)
approvals (id, tenant_id, batch_id, decided_by, decision, comment)
events (id, tenant_id, type, payload)
```

### API Endpoints

**Authentication**:
- POST `/auth/login` - User authentication
- POST `/auth/refresh` - Token refresh  
- POST `/auth/logout` - User logout

**Live Data**:
- GET `/inspections?since=<ISO>&limit=50` - Real-time inspections
- GET `/events?since=<ISO>&limit=100` - Event feed for alerts

**Batch Management**:
- GET `/batches` - List batches with aggregates
- GET `/batches/:id` - Batch details with audit log
- POST `/batches/:id/approve` - Approve batch (admin only)
- POST `/batches/:id/reject` - Reject batch (admin only)

**Analytics**:
- GET `/analytics/defect-rate?groupBy=vendor|style&range=last_7d|last_30d`
- GET `/analytics/throughput?bucket=day|week&range=last_7d|last_30d`  
- GET `/analytics/defect-types?range=last_7d|last_30d`
- GET `/analytics/approval-time?range=last_7d|last_30d`

**Exports**:
- POST `/exports/pdf` - Generate PDF report
- POST `/exports/csv` - Generate CSV export

**Mock & Admin**:
- POST `/admin/seed` - Seed database with demo data
- POST `/mock/inspections/start` - Start mock generator
- POST `/mock/inspections/stop` - Stop mock generator

### Frontend Architecture
- **Multi-tenant routing**: `/t/[tenantSlug]/[page]`
- **Real-time polling**: TanStack Query with 5s refetch intervals
- **Responsive design**: Mobile-friendly with desktop optimization
- **State management**: React Query for server state, React Context for auth
- **Type safety**: Full TypeScript with shared types package

### Security Features
- JWT-based authentication with refresh tokens
- Multi-tenant data isolation (tenant-scoped queries)
- Role-based access control (admin vs viewer)
- Presigned URLs for secure image access
- Password hashing with bcrypt (10 rounds)
- Input validation with Zod schemas

## 🛠️ Development

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ and pnpm (for local development)

### Local Development Setup
```bash
# Install dependencies
pnpm install

# Start services (database, minio, api)
docker compose up postgres minio minio-setup api -d

# Run frontend in development mode  
cd apps/web && pnpm dev

# Seed database
curl -X POST http://localhost:3001/admin/seed

# Start mock generator
curl -X POST http://localhost:3001/mock/inspections/start
```

### Project Structure
```
qa_dashboard/
├── apps/
│   ├── api/          # NestJS backend
│   └── web/          # Next.js frontend  
├── packages/
│   └── shared/       # Shared TypeScript types
├── database/
│   └── init.sql      # PostgreSQL schema
└── docker-compose.yml
```

## 🔄 Transitioning to Production

The codebase is designed for easy transition from mock data to real operator inputs:

1. **Replace mock endpoints**: Remove `/mock/*` routes
2. **Add operator interface**: Build mobile-friendly inspection forms  
3. **Real image upload**: Implement camera capture and upload to MinIO
4. **Webhook integration**: Add real-time notifications (Slack, email)
5. **Enhanced auth**: Integrate with enterprise SSO
6. **Scaling**: Add Redis for caching, load balancers, etc.

All core APIs (`/inspections`, `/batches`, `/analytics`, `/exports`) remain unchanged.

## 📈 Performance & Scalability

- **Database**: Optimized indexes for tenant-scoped queries
- **Caching**: TanStack Query with intelligent cache invalidation  
- **Images**: MinIO with presigned URLs (reduces server load)
- **Polling**: Efficient since-based incremental updates
- **Bundle size**: Optimized with Next.js 14 and proper code splitting

## 🐛 Troubleshooting

### Common Issues

**Services won't start**:
```bash
docker compose down -v  # Remove volumes
docker compose up --build
```

**Database connection errors**:
- Wait for PostgreSQL health check to pass
- Check logs: `docker compose logs postgres`

**Image loading issues**:  
- Verify MinIO is running: http://localhost:9001
- Check bucket permissions (should be public)

**Frontend build errors**:
```bash
cd apps/web && rm -rf .next node_modules && pnpm install
```

### Logs & Monitoring
```bash
# View all service logs
docker compose logs -f

# API logs only  
docker compose logs -f api

# Database logs
docker compose logs postgres
```

## 🔮 Next Steps

For production deployment:

1. **Environment Variables**: Configure for production
2. **SSL/TLS**: Add HTTPS certificates  
3. **Monitoring**: Add application monitoring (DataDog, New Relic)
4. **Backup**: Implement database backup strategy
5. **CDN**: Add CloudFront/CloudFlare for static assets
6. **Secrets**: Use proper secret management (AWS Secrets Manager)

---

**Built with ❤️ for Portuguese textile brands worldwide**

*Powered by Pack and Polish - the first Portuguese hub combining industrial finishing, labeling, and 100% computer vision inspection. This demo showcases production-ready patterns for AI-driven quality control with zero-defect guarantee.*

*"Be the reference post-production hub in Southern Europe, uniting AI and textile craftsmanship"*