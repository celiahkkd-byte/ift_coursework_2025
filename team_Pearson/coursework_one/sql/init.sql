DROP TABLE IF EXISTS systematic_equity.factor_observations;
DROP TABLE IF EXISTS systematic_equity.financial_observations;

CREATE SCHEMA IF NOT EXISTS systematic_equity;

CREATE TABLE systematic_equity.factor_observations (
    id SERIAL PRIMARY KEY,

    symbol VARCHAR(50) NOT NULL,
    observation_date DATE NOT NULL,
    factor_name VARCHAR(50) NOT NULL,
    factor_value NUMERIC(18,6),

    source VARCHAR(50),

    metric_frequency VARCHAR(20)
        CHECK (metric_frequency IN ('daily','weekly','monthly','quarterly','annual','unknown')),

    source_report_date DATE,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uniq_observation
    UNIQUE (symbol, observation_date, factor_name)
);

CREATE INDEX IF NOT EXISTS idx_factor_obs_symbol
    ON systematic_equity.factor_observations (symbol);

CREATE INDEX IF NOT EXISTS idx_factor_obs_observation_date
    ON systematic_equity.factor_observations (observation_date);

CREATE TABLE systematic_equity.financial_observations (
    id SERIAL PRIMARY KEY,

    symbol VARCHAR(50) NOT NULL,
    report_date DATE NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(18,6),

    currency VARCHAR(16),
    period_type VARCHAR(20)
        CHECK (period_type IN ('annual','quarterly','ttm','snapshot','unknown')),
    metric_definition VARCHAR(50)
        CHECK (metric_definition IN ('provider_reported','normalized','estimated','unknown')),

    source VARCHAR(50),
    as_of DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uniq_financial_observation
    UNIQUE (symbol, report_date, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_financial_obs_symbol
    ON systematic_equity.financial_observations (symbol);

CREATE INDEX IF NOT EXISTS idx_financial_obs_report_date
    ON systematic_equity.financial_observations (report_date);

CREATE TABLE IF NOT EXISTS systematic_equity.pipeline_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    run_date DATE NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('running', 'success', 'failed')),
    frequency VARCHAR(20),
    backfill_years INT,
    company_limit INT,
    enabled_extractors TEXT,
    rows_written INT DEFAULT 0,
    error_message TEXT,
    error_traceback TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run_date
    ON systematic_equity.pipeline_runs (run_date);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
    ON systematic_equity.pipeline_runs (status);
