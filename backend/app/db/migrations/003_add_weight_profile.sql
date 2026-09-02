-- Migration 003: Add weight profile to risk_scores

BEGIN;

-- Make code_sim_max nullable
ALTER TABLE risk_scores ALTER COLUMN code_sim_max DROP NOT NULL;
ALTER TABLE risk_scores ALTER COLUMN code_sim_max SET DEFAULT NULL;

-- Add weight_profile column
ALTER TABLE risk_scores ADD COLUMN weight_profile VARCHAR(20) NOT NULL DEFAULT 'code_present';

COMMIT;
