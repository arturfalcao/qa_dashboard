-- Migration: lot user assignments for scoped client access
-- Date: 2024-03-29

CREATE TABLE IF NOT EXISTS lot_user_assignments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lot_id UUID NOT NULL REFERENCES lots(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(lot_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_lot_user_assignments_lot_id ON lot_user_assignments(lot_id);
CREATE INDEX IF NOT EXISTS idx_lot_user_assignments_user_id ON lot_user_assignments(user_id);

CREATE TRIGGER update_lot_user_assignments_updated_at
  BEFORE UPDATE ON lot_user_assignments
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
