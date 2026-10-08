CREATE TABLE IF NOT EXISTS service_catalog (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name VARCHAR(160) NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  unit_price INTEGER NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
  currency VARCHAR(3) NOT NULL DEFAULT 'PKR',
  active BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX IF NOT EXISTS service_catalog_workspace_idx ON service_catalog (workspace_id);

CREATE TABLE IF NOT EXISTS service_packages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name VARCHAR(160) NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  price INTEGER NOT NULL DEFAULT 0 CHECK (price >= 0),
  currency VARCHAR(3) NOT NULL DEFAULT 'PKR',
  service_ids JSONB NOT NULL DEFAULT '[]',
  active BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX IF NOT EXISTS service_packages_workspace_idx ON service_packages (workspace_id);

CREATE TABLE IF NOT EXISTS pitch_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL,
  language VARCHAR(10) NOT NULL DEFAULT 'both',
  status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
  content JSONB NOT NULL DEFAULT '{}',
  selected_service_ids JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS pitch_documents_workspace_idx ON pitch_documents (workspace_id);
CREATE INDEX IF NOT EXISTS pitch_documents_lead_idx ON pitch_documents (lead_id);

CREATE TABLE IF NOT EXISTS pitch_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pitch_id UUID NOT NULL REFERENCES pitch_documents(id) ON DELETE CASCADE,
  phase VARCHAR(40) NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT NOT NULL,
  priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
  source_issue_ids JSONB NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS pitch_recommendations_pitch_idx ON pitch_recommendations (pitch_id);

CREATE TABLE IF NOT EXISTS share_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  pitch_id UUID NOT NULL REFERENCES pitch_documents(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS share_links_token_idx ON share_links (token_hash);

CREATE TABLE IF NOT EXISTS share_views (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  share_link_id UUID NOT NULL REFERENCES share_links(id) ON DELETE CASCADE,
  viewed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
