-- Migration: Add annotation and training run tables for auto model trainer
-- Run: psql -U academicguard -d academicguard < backend/app/db/migrations/002_add_annotations.sql

-- Create enum types
DO $$ BEGIN
    CREATE TYPE annotation_label AS ENUM ('human', 'ai_generated', 'plagiarized', 'mixed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE training_status AS ENUM ('pending', 'running', 'completed', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Annotations table: instructor-provided ground-truth labels for submissions
CREATE TABLE IF NOT EXISTS annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label annotation_label NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (submission_id)  -- One annotation per submission
);

CREATE INDEX IF NOT EXISTS ix_annotations_submission ON annotations(submission_id);
CREATE INDEX IF NOT EXISTS ix_annotations_user ON annotations(user_id);
CREATE INDEX IF NOT EXISTS ix_annotations_label ON annotations(label);

-- Training runs table: tracks each model training execution
CREATE TABLE IF NOT EXISTS training_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status training_status NOT NULL DEFAULT 'pending',
    samples_count INT NOT NULL DEFAULT 0,
    accuracy FLOAT,
    roc_auc FLOAT,
    f1_score FLOAT,
    precision_score FLOAT,
    recall_score FLOAT,
    model_path TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    training_config JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_training_runs_user ON training_runs(user_id);
CREATE INDEX IF NOT EXISTS ix_training_runs_active ON training_runs(is_active) WHERE is_active = TRUE;
