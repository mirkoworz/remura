-- REMURA Gateway Lab v0.8.2 — aggiornamento 11/11/2026 17:46 CET
-- SQL SCHEMA DI RICERCA, NON APPLICATO SU ALCUN DATABASE.
-- Non eseguire su DB Oracle/REMURA produzione. Esclusivamente D1 isolato LAB.
CREATE TABLE IF NOT EXISTS tv_flow_events (
  event_key TEXT NOT NULL PRIMARY KEY,
  received_at_ms INTEGER NOT NULL,
  bar_close_ms INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('BAR_EVENT', 'HEARTBEAT')),
  version TEXT NOT NULL,
  is_timely INTEGER NOT NULL CHECK (is_timely IN (0, 1)),
  raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tv_flow_events_received
  ON tv_flow_events(received_at_ms);
CREATE INDEX IF NOT EXISTS idx_tv_flow_events_symbol_close
  ON tv_flow_events(symbol, timeframe, bar_close_ms);

-- Retention soltanto quando esplicitamente autorizzata:
-- DELETE FROM tv_flow_events WHERE received_at_ms < [cutoff_ms];
-- Evitare job automatici finché non è stato stabilito un backup/test restore.
