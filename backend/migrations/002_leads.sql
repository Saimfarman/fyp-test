CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  provider_place_id VARCHAR(180) NOT NULL,
  name VARCHAR(240) NOT NULL,
  category VARCHAR(120),
  address TEXT,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  phone VARCHAR(80),
  website_url TEXT,
  website_status VARCHAR(20) NOT NULL DEFAULT 'NO_WEBSITE',
  severity VARCHAR(20) NOT NULL DEFAULT 'UNSCANNED',
  opportunity_score INTEGER NOT NULL DEFAULT 0,
  lead_value_tier VARCHAR(20) NOT NULL DEFAULT 'LOW',
  rating DOUBLE PRECISION,
  review_count INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, provider_place_id),
  CHECK (website_status IN ('NO_WEBSITE', 'SOCIAL_ONLY', 'DEAD_SITE', 'HAS_WEBSITE')),
  CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNSCANNED'))
);
CREATE INDEX IF NOT EXISTS leads_workspace_location_idx ON leads (workspace_id, latitude, longitude);
