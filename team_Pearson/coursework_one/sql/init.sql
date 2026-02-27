DROP TABLE IF EXISTS systematic_equity.factor_observations;

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
