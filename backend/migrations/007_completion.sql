ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS company_name VARCHAR(160);
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS logo_url TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS brand_color VARCHAR(7) NOT NULL DEFAULT '#ff7548';
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS default_city VARCHAR(80) NOT NULL DEFAULT 'Karachi';
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS custom_domain VARCHAR(255);

CREATE TABLE IF NOT EXISTS workspace_invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  email VARCHAR(320) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'sales',
  token_hash VARCHAR(128) NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  accepted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (role IN ('owner', 'manager', 'sales', 'developer'))
);
CREATE INDEX IF NOT EXISTS workspace_invitations_workspace_idx ON workspace_invitations(workspace_id);
