-- REMURA v0.8.115 LAB — 17/11/2026 CET
-- Separate NEW fixture database only. Never apply to existing CVD D1.
CREATE TABLE level_admission_v1 (
 id INTEGER PRIMARY KEY CHECK(id=1),
 pin TEXT NOT NULL CHECK(length(pin)=64 AND pin NOT GLOB '*[^0-9a-f]*'),
 enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
 attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 48),
 last_ms INTEGER,
 window_count INTEGER NOT NULL DEFAULT 0 CHECK(window_count BETWEEN 0 AND 20),
 allowed INTEGER NOT NULL DEFAULT 0 CHECK(allowed IN (0,1)),
 CHECK(window_count<=attempts),
 CHECK((attempts=0 AND last_ms IS NULL AND window_count=0 AND allowed=0)
 OR (attempts>0 AND last_ms BETWEEN 1 AND 4102444799999 AND window_count>0))
);
-- No insert, enable, or migration in this file.
