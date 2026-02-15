-- CW1 minimal SQL bootstrap for factor storage.
-- Role 3/5 can extend this with production-ready constraints and indexing strategy.

CREATE SCHEMA IF NOT EXISTS systematic_equity;

CREATE TABLE IF NOT EXISTS systematic_equity.factor_observations (
    company_id TEXT NOT NULL,
    as_of_date DATE NOT NULL,
    factor_name TEXT NOT NULL,
    factor_value DOUBLE PRECISION,
    source TEXT NOT NULL,
    metric_frequency TEXT NOT NULL,
    source_report_date DATE,
    run_id TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_factor_obs UNIQUE (company_id, factor_name, as_of_date)
);

CREATE INDEX IF NOT EXISTS idx_factor_obs_company_id
    ON systematic_equity.factor_observations (company_id);

CREATE INDEX IF NOT EXISTS idx_factor_obs_as_of_date
    ON systematic_equity.factor_observations (as_of_date);

-- Example UPSERT pattern (for reference):
-- INSERT INTO systematic_equity.factor_observations (
--     company_id, as_of_date, factor_name, factor_value, source,
--     metric_frequency, source_report_date, run_id
-- ) VALUES (...)
-- ON CONFLICT (company_id, factor_name, as_of_date)
-- DO UPDATE SET
--     factor_value = EXCLUDED.factor_value,
--     source = EXCLUDED.source,
--     metric_frequency = EXCLUDED.metric_frequency,
--     source_report_date = EXCLUDED.source_report_date,
--     run_id = EXCLUDED.run_id,
--     updated_at = NOW();
