-- Migration: Enhanced Photo Documentation and Process Tracking Features
-- Date: 2025-09-22

-- Create new enums
CREATE TYPE defect_severity AS ENUM ('critical', 'major', 'minor');
CREATE TYPE photo_angle AS ENUM ('front', 'back', 'side_left', 'side_right', 'detail_macro', 'hanging', 'flat_lay');
CREATE TYPE process_station AS ENUM ('receiving', 'initial_inspection', 'ironing', 'folding', 'quality_check', 'packing', 'final_inspection', 'dispatch');
CREATE TYPE batch_priority AS ENUM ('low', 'normal', 'high', 'urgent');

-- Update defect_type enum to include new types
ALTER TYPE defect_type ADD VALUE 'fabric_defect';
ALTER TYPE defect_type ADD VALUE 'hardware_issue';
ALTER TYPE defect_type ADD VALUE 'discoloration';
ALTER TYPE defect_type ADD VALUE 'tear_damage';

-- Add new columns to inspections table
ALTER TABLE inspections ADD COLUMN defect_severity defect_severity;
ALTER TABLE inspections ADD COLUMN process_station process_station DEFAULT 'initial_inspection';
ALTER TABLE inspections ADD COLUMN assigned_worker VARCHAR(255);
ALTER TABLE inspections ADD COLUMN temperature DECIMAL(4,1);
ALTER TABLE inspections ADD COLUMN humidity DECIMAL(4,1);
ALTER TABLE inspections ADD COLUMN lighting_level DECIMAL(6,1);
ALTER TABLE inspections ADD COLUMN quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 100);

-- Add new columns to batches table
ALTER TABLE batches ADD COLUMN current_station process_station DEFAULT 'receiving';
ALTER TABLE batches ADD COLUMN estimated_completion_time TIMESTAMPTZ;
ALTER TABLE batches ADD COLUMN priority batch_priority DEFAULT 'normal';

-- Create inspection_photos table
CREATE TABLE inspection_photos (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  inspection_id UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
  angle photo_angle NOT NULL,
  photo_key VARCHAR(255) NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create photo_annotations table
CREATE TABLE photo_annotations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  photo_id UUID NOT NULL REFERENCES inspection_photos(id) ON DELETE CASCADE,
  created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  x DECIMAL(5,2) NOT NULL CHECK (x >= 0 AND x <= 100),
  y DECIMAL(5,2) NOT NULL CHECK (y >= 0 AND y <= 100),
  comment TEXT NOT NULL,
  defect_type defect_type,
  defect_severity defect_severity,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create batch_process_progress table
CREATE TABLE batch_process_progress (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  batch_id UUID NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
  station process_station NOT NULL,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  assigned_worker UUID REFERENCES users(id),
  notes TEXT,
  quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 100),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(batch_id, station)
);

-- Create indexes for new tables
CREATE INDEX idx_inspection_photos_tenant_id ON inspection_photos(tenant_id);
CREATE INDEX idx_inspection_photos_inspection_id ON inspection_photos(inspection_id);
CREATE INDEX idx_inspection_photos_tenant_inspection ON inspection_photos(tenant_id, inspection_id);

CREATE INDEX idx_photo_annotations_tenant_id ON photo_annotations(tenant_id);
CREATE INDEX idx_photo_annotations_photo_id ON photo_annotations(photo_id);
CREATE INDEX idx_photo_annotations_created_by ON photo_annotations(created_by);
CREATE INDEX idx_photo_annotations_tenant_photo ON photo_annotations(tenant_id, photo_id);

CREATE INDEX idx_batch_process_progress_tenant_id ON batch_process_progress(tenant_id);
CREATE INDEX idx_batch_process_progress_batch_id ON batch_process_progress(batch_id);
CREATE INDEX idx_batch_process_progress_tenant_batch ON batch_process_progress(tenant_id, batch_id);
CREATE INDEX idx_batch_process_progress_station ON batch_process_progress(tenant_id, station);
CREATE INDEX idx_batch_process_progress_assigned_worker ON batch_process_progress(assigned_worker);

-- Create additional indexes for new columns
CREATE INDEX idx_inspections_process_station ON inspections(tenant_id, process_station);
CREATE INDEX idx_inspections_quality_score ON inspections(tenant_id, quality_score);
CREATE INDEX idx_inspections_defect_severity ON inspections(tenant_id, defect_severity);

CREATE INDEX idx_batches_current_station ON batches(tenant_id, current_station);
CREATE INDEX idx_batches_priority ON batches(tenant_id, priority);
CREATE INDEX idx_batches_estimated_completion ON batches(tenant_id, estimated_completion_time);

-- Create triggers for updated_at on new tables
CREATE TRIGGER update_batch_process_progress_updated_at
  BEFORE UPDATE ON batch_process_progress
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add constraints to ensure data consistency
ALTER TABLE inspections
  ADD CONSTRAINT check_defect_severity
  CHECK (
    (has_defect = FALSE AND defect_severity IS NULL) OR
    (has_defect = TRUE)
  );

-- Update existing constraint to handle new defect types
ALTER TABLE inspections
  DROP CONSTRAINT inspections_check;

ALTER TABLE inspections
  ADD CONSTRAINT inspections_check
  CHECK (
    (has_defect = FALSE AND defect_type IS NULL) OR
    (has_defect = TRUE AND defect_type IS NOT NULL)
  );