-- Migration: Add marking configuration to batches and marks to submissions
-- This migration adds support for marking configuration and mark tracking

-- Add marking columns to batches table
ALTER TABLE batches ADD COLUMN IF NOT EXISTS total_marks FLOAT NULL;
ALTER TABLE batches ADD COLUMN IF NOT EXISTS marking_config JSONB NULL;

-- Add marking columns to submissions table
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS marks_obtained FLOAT NULL;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS marks_breakdown JSONB NULL;

-- Create index for marking queries
CREATE INDEX IF NOT EXISTS ix_submissions_marks ON submissions(batch_id, marks_obtained DESC);
