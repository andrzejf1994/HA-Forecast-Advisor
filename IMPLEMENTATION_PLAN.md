# IMPLEMENTATION_PLAN.md

## Definition of Done
Każde zadanie:
- [ ] implementacja;
- [ ] happy-path test;
- [ ] error-path test;
- [ ] regression test, jeśli dotyczy;
- [ ] type check;
- [ ] lint;
- [ ] zero real network;
- [ ] dokumentacja;
- [ ] brak sekretów;
- [ ] unload/reload test, jeśli dotyczy;
- [ ] migracja, jeśli zmienia schema.

## Epic 0 — fundament
- FF-001: repo i manifest.
- FF-002: config flow, translations.
- FF-003: coordinator, setup/unload.
- FF-004: CI, lint, typing, coverage.
- FF-005: dokumentacja i AGENTS.md.

## Epic 1 — pobieranie
- FF-101: modele ForecastPoint/Snapshot.
- FF-102: adapter weather.get_forecasts.
- FF-103: normalizacja i jednostki.
- FF-104: scheduler interwałów.
- FF-105: deduplikacja i source health.
- FF-106: repository historii.
- FF-107: retencja.

## Epic 2 — obserwacje
- FF-201: config per parametr.
- FF-202: encje observation.
- FF-203: manual observation action.
- FF-204: ręczny deszcz.
- FF-205: time matching.
- FF-206: korekta/usunięcie obserwacji.

## Epic 3 — scoring
- FF-301: MAE/bias.
- FF-302: Brier i rain classification.
- FF-303: stability/correction benefit.
- FF-304: lead buckets.
- FF-305: aggregates/sample status.
- FF-306: shrinkage.

## Epic 4 — fusion
- FF-401: weight model.
- FF-402: weighted median.
- FF-403: two-stage rain.
- FF-404: uncertainty/confidence.
- FF-405: fused hourly forecast.
- FF-406: source contribution diagnostics.

## Epic 5 — periods/outputs
- FF-501: period models.
- FF-502: DST-safe aggregation.
- FF-503: output definitions CRUD.
- FF-504: weather entity.
- FF-505: sensors/binary sensors.
- FF-506: templates/preview.

## Epic 6 — comfort
- FF-601: clothing items.
- FF-602: outfits.
- FF-603: context profiles.
- FF-604: feedback action/storage.
- FF-605: threshold learning.
- FF-606: comfort prediction.
- FF-607: whole-day optimizer.
- FF-608: optional helper entities.

## Epic 7 — panel
- FF-701: WebSocket schemas/API.
- FF-702: overview.
- FF-703: source accuracy.
- FF-704: observation editor.
- FF-705: feedback and thresholds.
- FF-706: clothing editor.
- FF-707: outputs/templates/settings.

## Epic 8 — AI
- FF-801: provider interface.
- FF-802: Conversation Agent.
- FF-803: OpenAI-compatible/Ollama.
- FF-804: bounded context.
- FF-805: structured response/fallback.
- FF-806: privacy/security tests.

## Epic 9 — release
- FF-901: diagnostics.
- FF-902: repairs.
- FF-903: export/import.
- FF-904: migration matrix.
- FF-905: performance benchmark.
- FF-906: README/user docs.
- FF-907: beta.
- FF-908: 1.0 release.
