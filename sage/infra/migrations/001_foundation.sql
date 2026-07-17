-- Sage MVP Migration
-- Phase 01: Foundation — Postgres schema

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Event log table (append-only, source of truth for async events)
CREATE TABLE IF NOT EXISTS event_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    source VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_id UUID NOT NULL DEFAULT gen_random_uuid(),
    correlation_id UUID,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(event_id)
);

CREATE INDEX IF NOT EXISTS idx_event_log_type_time 
ON event_log(event_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_event_log_correlation 
ON event_log(correlation_id);

CREATE INDEX IF NOT EXISTS idx_event_log_unprocessed 
ON event_log(processed) WHERE processed = FALSE;

-- Audit log (Phase 17: Security)
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    subject VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource_tier INT NOT NULL DEFAULT 0,
    resource_ref VARCHAR(100),
    outcome VARCHAR(50) NOT NULL,
    context JSONB DEFAULT '{}',
    session_id UUID
);

CREATE INDEX IF NOT EXISTS idx_audit_log_time 
ON audit_log(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_subject 
ON audit_log(subject, timestamp DESC);

-- System health tracking
CREATE TABLE IF NOT EXISTS system_health (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    subsystem VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    latency_ms FLOAT,
    error_count INT DEFAULT 0,
    details JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_system_health_subsystem 
ON system_health(subsystem, timestamp DESC);

-- LLM Router usage tracking
CREATE TABLE IF NOT EXISTS llm_usage (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    operation VARCHAR(50) NOT NULL,
    latency_ms FLOAT,
    tokens_input INT DEFAULT 0,
    tokens_output INT DEFAULT 0,
    cost_estimate FLOAT DEFAULT 0,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_provider 
ON llm_usage(provider, timestamp DESC);

-- Insert initial system event
INSERT INTO event_log (event_type, payload, source, processed)
VALUES ('system.started', '{"version": "v4.0.0", "phase": "01"}', 'system', TRUE);

-- Create notification function for LISTEN/NOTIFY
CREATE OR REPLACE FUNCTION notify_event()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify(NEW.event_type, json_build_object(
        'event_id', NEW.event_id,
        'event_type', NEW.event_type,
        'payload', NEW.payload,
        'source', NEW.source,
        'timestamp', NEW.timestamp,
        'correlation_id', NEW.correlation_id
    )::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS event_notify ON event_log;

-- Create trigger
CREATE TRIGGER event_notify
    AFTER INSERT ON event_log
    FOR EACH ROW
    EXECUTE FUNCTION notify_event();
