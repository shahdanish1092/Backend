-- Migration 015: Add google_account_email to google_tokens

ALTER TABLE google_tokens
ADD COLUMN IF NOT EXISTS google_account_email TEXT;
