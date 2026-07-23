# AGENTS.md — instrukcje dla Codex

## Misja
Zaimplementuj `forecast_fusion` zgodnie z `TECHNICAL_SPECIFICATION.md`.

## Reguły
1. Przeczytaj specyfikację przed zmianą.
2. Przed kodem przygotuj plan.
3. Rób małe, logiczne zmiany.
4. Każda funkcja ma testy.
5. Każdy bug ma test regresyjny.
6. Nie kończ zadania przy czerwonych testach.
7. Nie używaj sieci w testach.
8. Nie zapisuj sekretów.
9. Nie upraszczaj architektury bez opisania odstępstwa.
10. Aktualizuj dokumentację.

## Architektura
- `core/` bez zależności od HA.
- Encje nie pobierają danych.
- Coordinator współdzieli wyniki.
- Storage za interfejsem repository.
- Daty timezone-aware UTC.
- Brak globalnego mutowalnego stanu.
- Preferuj immutable dataclasses.
- Deterministyczne tie-breaki.

## Home Assistant
- config flow/options/reconfigure;
- `ConfigEntry.runtime_data`;
- `DataUpdateCoordinator`;
- poprawny setup/unload/reload;
- actions w `async_setup`;
- translations/en.json i pl.json;
- weather.get_forecasts;
- stabilne unique IDs;
- diagnostic entities disabled by default.

## Algorytmy
- trafność != stabilność;
- brak jednej globalnej oceny źródła;
- scoring per parametr/horyzont;
- shrinkage małej próby;
- fusion odporne na outlier;
- confidence wyjaśnialne;
- LLM nie zmienia modelu;
- izolacja użytkownika/transportu/outfitu;
- ograniczony krok uczenia.

## Storage
- wersjonowane, idempotentne migracje;
- brak utraty danych przy błędzie;
- batch retention;
- brak wielkiego stale przepisywanego JSON;
- eksport bez sekretów.

## Obowiązkowe testy
```bash
ruff check .
ruff format --check .
mypy custom_components/forecast_fusion
python -m pytest -q
```

Dodatkowo Hassfest/HACS, jeśli dostępne.

Pokrycie:
- całość >=90%;
- krytyczne moduły >=95%;
- config flow pełne pokrycie;
- DST;
- unload;
- property tests fusion/learning.

## Styl
- pełne type hints;
- docstrings public API;
- angielskie identyfikatory;
- UI przez tłumaczenia;
- brak broad exception bez uzasadnienia;
- brak ignorowania type errors;
- brak zbędnych zależności.

## Bezpieczeństwo
- limity inputów;
- walidacja dat/liczb;
- maskowanie credentials;
- SSL default on;
- timeout AI;
- schema validation;
- brak wykonywania kodu/URL z LLM;
- bounded prompt context.

## Raport końcowy zadania
Podaj:
1. podsumowanie;
2. zmienione obszary;
3. komendy;
4. wyniki testów;
5. ograniczenia;
6. migracje;
7. aktualizację dokumentacji.

## Niedozwolone skróty
- bezpośrednie API zamiast weather.get_forecasts;
- jedna ogólna ocena providera;
- stabilność jako trafność;
- automatyczne tworzenie wielu encji;
- pominięcie manualnego deszczu;
- mieszanie transportów;
- wymagany LLM;
- sekrety w diagnostyce;
- funkcja bez testów;
- TODO w produkcyjnej ścieżce.
