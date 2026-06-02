CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    policy_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_devices_updated_at ON devices (updated_at);
