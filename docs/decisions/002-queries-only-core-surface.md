# ADR-002: core/queries as the Only Core Surface for apps/api

## Status
Accepted

## Context
`apps/api` needs to serve intelligence data (signals, radar, cases, entities) that is built by core analytics engines. Without a clear boundary, the API could directly import typology logic, ER algorithms, and risk scoring — exposing these to anyone reading the API codebase.

## Decision
A dedicated `core/queries/openwatch_queries` package exposes **only pre-computed, stored results** from the database. The API:
- MAY import `openwatch_queries` (read-only derived intelligence)
- MUST NOT import `openwatch_typologies`, `openwatch_er`, `openwatch_analytics`, `openwatch_baselines` directly

This is enforced by `.import-linter` contract `api-cannot-import-detectors-directly`.

## Consequences
- Core intelligence engines remain opaque to API contributors
- The intelligence pipeline (worker) is the only writer; the API is a pure reader
- Adding a new radar metric requires changing `core/queries` + running a pipeline step — deliberate architectural friction that prevents leakage by accident
