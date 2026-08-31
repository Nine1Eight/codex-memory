BEGIN;

CREATE TABLE tenants (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  data_region TEXT NOT NULL DEFAULT 'us',
  retention_policy_json TEXT NOT NULL DEFAULT '{}',
  tenant_id TEXT NOT NULL DEFAULT ''
);

CREATE TABLE principals (
  id TEXT PRIMARY KEY,
  oidc_issuer TEXT NOT NULL,
  oidc_subject TEXT NOT NULL,
  email_normalized TEXT NOT NULL,
  display_name TEXT NOT NULL DEFAULT '',
  UNIQUE (oidc_issuer, oidc_subject)
);

CREATE TABLE memberships (
  tenant_id TEXT NOT NULL,
  principal_id TEXT NOT NULL,
  role TEXT NOT NULL,
  PRIMARY KEY (tenant_id, principal_id)
);

CREATE TABLE agents (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  did_key_id TEXT NOT NULL,
  public_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  UNIQUE (tenant_id, name)
);

CREATE TABLE agent_versions (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  semantic_version TEXT NOT NULL,
  config_json TEXT NOT NULL,
  config_sha256 TEXT NOT NULL,
  immutable INTEGER NOT NULL DEFAULT 1,
  UNIQUE (agent_id, semantic_version),
  UNIQUE (agent_id, config_sha256)
);

CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  title TEXT NOT NULL,
  current_revision_id TEXT,
  immutable INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE source_revisions (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  revision_number INTEGER NOT NULL,
  fingerprint_sha256 TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  duration_ms INTEGER,
  immutable INTEGER NOT NULL DEFAULT 1,
  UNIQUE (source_id, revision_number),
  UNIQUE (source_id, fingerprint_sha256)
);

CREATE TABLE authority_grants (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  authority_class TEXT NOT NULL,
  status TEXT NOT NULL,
  valid_from TEXT NOT NULL,
  valid_until TEXT
);

CREATE TABLE audit_events (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  occurred_at TEXT NOT NULL
);

CREATE TABLE bootstrap_views (
  tenant_id TEXT NOT NULL,
  source_fingerprint_sha256 TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_revision_id TEXT NOT NULL,
  receipt_id TEXT NOT NULL,
  objective_type TEXT NOT NULL,
  view_class TEXT NOT NULL,
  qualified INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (tenant_id, source_fingerprint_sha256)
);

CREATE TABLE oauth_tokens (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  principal_id TEXT NOT NULL,
  encrypted_blob_json TEXT NOT NULL,
  revoked_at TEXT,
  immutable INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE signing_keys (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  key_id TEXT NOT NULL UNIQUE,
  provider_reference TEXT NOT NULL,
  public_key TEXT NOT NULL,
  status TEXT NOT NULL,
  activated_at TEXT NOT NULL,
  revoked_at TEXT,
  reason TEXT
);

CREATE INDEX idx_sources_tenant ON sources(tenant_id);
CREATE INDEX idx_revisions_tenant ON source_revisions(tenant_id);
CREATE INDEX idx_grants_tenant ON authority_grants(tenant_id);
CREATE INDEX idx_audit_tenant ON audit_events(tenant_id);
CREATE INDEX idx_bootstrap_views_tenant ON bootstrap_views(tenant_id);

COMMIT;
