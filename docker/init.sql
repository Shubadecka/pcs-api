-- Enable UUID extension (required for gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable pgvector extension (required for vector embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS entries CASCADE;
DROP TABLE IF EXISTS pages CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Create sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_token ON sessions(session_token);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);

-- Create pages table
CREATE TABLE pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_path VARCHAR(512) NOT NULL,
    uploaded_date DATE NOT NULL,
    page_start_date DATE,
    page_end_date DATE,
    notes TEXT,
    page_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (page_status IN ('pending', 'transcribed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pages_user_id ON pages(user_id);
CREATE INDEX idx_pages_user_uploaded_date ON pages(user_id, uploaded_date);
CREATE INDEX idx_pages_user_page_status ON pages(user_id, page_status);
CREATE INDEX idx_pages_user_date_range ON pages(user_id, page_start_date, page_end_date);

-- Create entries table (entries only created once page has been transcribed)
-- NOTE: embedding dimension (1024) must match the EMBEDDING_DIM env var.
-- If you change the model/dimension, you must rebuild this container or run:
--   ALTER TABLE entries ALTER COLUMN embedding TYPE vector(N);
CREATE TABLE entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    entry_date DATE NOT NULL,
    raw_ocr_transcription TEXT NOT NULL,
    improved_transcription TEXT NULL,
    agent_has_improved BOOLEAN NOT NULL DEFAULT FALSE,
    embedding vector(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_entries_user_id ON entries(user_id);
CREATE INDEX idx_entries_user_entry_date ON entries(user_id, entry_date);
CREATE INDEX idx_entries_page_id ON entries(page_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at on entries
CREATE TRIGGER update_entries_updated_at
    BEFORE UPDATE ON entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create transcription_learnings table
-- This table is used to store the learnings of the agentic loop for improving future agentic improvements to the transcription.
-- Just a placeholder for now, will be used later.
CREATE TABLE transcription_learnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entry_id UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    learning_date DATE NOT NULL,
    learning_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transcription_learnings_user_id ON transcription_learnings(user_id);
CREATE INDEX idx_transcription_learnings_entry_id ON transcription_learnings(entry_id);
CREATE INDEX idx_transcription_learnings_user_learning_date ON transcription_learnings(user_id, learning_date);