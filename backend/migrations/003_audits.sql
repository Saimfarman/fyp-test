CREATE TABLE IF NOT EXISTS audits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED',
  overall_score INTEGER NOT NULL DEFAULT 0 CHECK (overall_score BETWEEN 0 AND 100),
  category_scores JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_issues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  audit_id UUID NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
  rule_id VARCHAR(80) NOT NULL,
  category VARCHAR(40) NOT NULL,
  severity VARCHAR(20) NOT NULL,
  confidence INTEGER NOT NULL DEFAULT 100 CHECK (confidence BETWEEN 0 AND 100),
  affected_url TEXT NOT NULL,
  explanation TEXT NOT NULL,
  fix_recommendation TEXT NOT NULL,
  evidence JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS audit_issues_audit_idx ON audit_issues (audit_id);
