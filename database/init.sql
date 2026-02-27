-- ── Database initialisation ──────────────────────────────────────────────────
-- Runs automatically when the Postgres container starts for the first time.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- provides gen_random_uuid()

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ  NOT NULL    DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL    DEFAULT NOW()
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID         NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20)  NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT         NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at  ON messages(created_at);

-- Auto-update updated_at on conversations when a new message is added
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    UPDATE conversations SET updated_at = NOW() WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_update_conversation ON messages;
CREATE TRIGGER trg_update_conversation
    AFTER INSERT ON messages
    FOR EACH ROW EXECUTE FUNCTION update_conversation_timestamp();

-- Seed a welcome message for demonstration
INSERT INTO conversations(id) VALUES ('00000000-0000-0000-0000-000000000001') ON CONFLICT DO NOTHING;
INSERT INTO messages(conversation_id, role, content)
    VALUES ('00000000-0000-0000-0000-000000000001', 'assistant', 'Hello! I am TinyLlama. How can I help you today?')
    ON CONFLICT DO NOTHING;
