BEGIN;
CREATE TABLE IF NOT EXISTS meetings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL,
  title TEXT,
  source_type TEXT DEFAULT 'audio',
  transcript TEXT,
  summary TEXT,
  action_items JSONB,
  participants TEXT[],
  meeting_date DATE,
  duration_minutes INTEGER,
  status TEXT NOT NULL DEFAULT 'processing',
  n8n_execution_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_meetings_user_email ON meetings(user_email);
COMMIT;
