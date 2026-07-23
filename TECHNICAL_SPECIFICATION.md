# Forecast Fusion & Personal Comfort
## Kompletna specyfikacja techniczna integracji Home Assistant

**Domena robocza:** `forecast_fusion`  
**Typ:** Home Assistant Custom Integration  
**Główny język:** Python  
**Status:** dokument implementacyjny dla Codex

---

## 1. Wizja i cel

Integracja ma pobierać prognozy z wybranych encji `weather.*` przez akcję `weather.get_forecasts`, zapisywać kolejne wersje prognoz, porównywać je z późniejszymi obserwacjami rzeczywistymi, oceniać trafność źródeł dla poszczególnych parametrów i horyzontów czasowych, a następnie budować prognozę zbiorczą.

Druga warstwa ma przewidywać komfort użytkownika oraz optymalny ubiór dla:
- całego dnia;
- pojedynczej godziny;
- zakresu godzin;
- nazwanych okresów, np. dojazdu i powrotu;
- określonego transportu i aktywności.

Użytkownik sam wybiera:
- źródła prognozy;
- interwały pobierania;
- retencję;
- źródła obserwacji rzeczywistych per parametr;
- tworzone encje;
- zakresy godzin;
- zestawy ubioru;
- teksty i placeholdery;
- strategię rekomendacji;
- opcjonalnego providera AI.

Integracja musi działać w pełni bez LLM.

---

## 2. Cele produktu

1. Lokalna ocena jakości prognoz.
2. Osobne rankingi źródeł per parametr i horyzont.
3. Oddzielenie trafności, stabilności i użyteczności korekt.
4. Budowanie odpornej na odstające źródła prognozy zbiorczej.
5. Wyznaczanie niepewności i powodów obniżonej pewności.
6. Konfigurowalne okresy analizy.
7. Konfigurowalne encje wynikowe.
8. Konfigurowalne szablony tekstowe.
9. Ręczne i automatyczne obserwacje rzeczywiste.
10. Uczenie osobistych granic komfortu.
11. Rekomendowanie zestawu na okres i cały dzień.
12. Opcjonalna analiza przez Conversation Agent, Ollama lub OpenAI-compatible API.
13. Pełna diagnostyka, eksport, migracje i testy.

## 3. Poza zakresem MVP

- bezpośrednie API dostawców pogody;
- radar pogodowy;
- śledzenie trasy;
- sieci neuronowe;
- automatyczna zmiana parametrów przez LLM;
- synchronizacja chmurowa;
- medyczny lub fizjologiczny model termoregulacji.

---

## 4. Zasady architektoniczne

### 4.1. Lokalność
Prognozy, obserwacje, feedback i modele są przechowywane lokalnie. Dane są wysyłane poza HA tylko po świadomym skonfigurowaniu AI.

### 4.2. Wyjaśnialność
Każda wynikowa wartość i rekomendacja musi udostępniać:
- źródła składowe;
- ich wagi;
- metodę agregacji;
- confidence;
- reason codes;
- profil komfortu;
- wersję modelu.

### 4.3. Odporność
Awaria jednego źródła nie zatrzymuje integracji. Brak obserwacji jednego parametru nie blokuje innych.

### 4.4. Rozdzielenie warstw
- `core/`: modele i algorytmy bez zależności od HA;
- warstwa HA: config flow, coordinator, encje, akcje;
- repositories: storage;
- optional AI: wyłącznie opis i dodatkowa analiza.

---

## 5. Pobieranie prognoz

Prognozy są pobierane z istniejących encji `weather.*` wyłącznie przez `weather.get_forecasts`.

Przykład logiczny:

```yaml
action: weather.get_forecasts
target:
  entity_id:
    - weather.open_meteo
    - weather.met_no
data:
  type: hourly
response_variable: forecast_response
```

Konfiguracja źródła:

```yaml
id: open_meteo_home
entity_id: weather.open_meteo
enabled: true
forecast_types: [hourly]
poll_interval_minutes: 30
initial_weight: 1.0
included_fields:
  - temperature
  - apparent_temperature
  - precipitation_probability
  - precipitation
  - wind_speed
  - wind_gust
  - cloud_coverage
```

Wymagania:
- każdy provider może zwracać inny zestaw pól;
- brak pola nie jest błędem całego źródła;
- identyczne snapshoty są deduplikowane;
- źródło ma health status i datę ostatniego sukcesu;
- użytkownik ustala interwał;
- UI ostrzega przy bardzo krótkim interwale;
- ręczna akcja `forecast_fusion.refresh`;
- timeout, kontrolowany retry i brak równoległego pobrania tego samego źródła;
- pierwsze pobranie przez `async_config_entry_first_refresh()`.

---

## 6. Modele danych prognozy

```python
@dataclass(frozen=True, slots=True)
class ForecastPoint:
    source_id: str
    forecast_type: ForecastType
    fetched_at: datetime
    issued_at: datetime | None
    valid_at: datetime
    lead_time: timedelta

    temperature_c: float | None
    apparent_temperature_c: float | None
    dew_point_c: float | None
    humidity_pct: float | None
    pressure_hpa: float | None

    precipitation_probability_pct: float | None
    precipitation_mm: float | None
    snow_mm: float | None

    wind_speed_ms: float | None
    wind_gust_ms: float | None
    wind_bearing_deg: float | None

    cloud_cover_pct: float | None
    uv_index: float | None
    condition: str | None
    raw_hash: str
```

Zasady:
- wszystkie daty timezone-aware;
- wewnętrznie UTC;
- jednostki wewnętrzne stałe;
- `NaN` i infinity odrzucane;
- wilgotność i prawdopodobieństwo w `0..100`;
- wiatr normalizowany;
- nieznany condition zachowywany diagnostycznie;
- wejście nie jest mutowane;
- `lead_time` liczony od `issued_at`, a przy jego braku od `fetched_at`.

Snapshot:

```python
@dataclass(frozen=True, slots=True)
class ForecastSnapshot:
    snapshot_id: str
    source_id: str
    fetched_at: datetime
    forecast_type: ForecastType
    points: tuple[ForecastPoint, ...]
    raw_hash: str
```

---

## 7. Harmonogram i retencja

Użytkownik konfiguruje niezależnie:
- interwał pollingu;
- horyzonty oceny;
- retencję surowych prognoz;
- retencję obserwacji;
- retencję wyników weryfikacji;
- retencję feedbacku;
- retencję agregatów.

```yaml
retention:
  raw_forecasts_days: 90
  observations_days: 365
  verification_results_days: 365
  comfort_feedback_days: 0
  aggregated_statistics_days: 0
```

`0` oznacza bezterminowo.

Retencja:
- działa okresowo i ręcznie;
- kasuje partiami;
- nie blokuje event loop;
- ma tryb dry-run;
- zachowuje agregaty po usunięciu surowych danych;
- raportuje liczbę rekordów.

---

## 8. Obserwacje rzeczywiste

Konfiguracja per parametr:

```yaml
observations:
  temperature:
    mode: entity
    entity_id: sensor.outdoor_temperature
  humidity:
    mode: entity
    entity_id: sensor.outdoor_humidity
  precipitation_occurrence:
    mode: manual
  precipitation_amount:
    mode: disabled
  wind_speed:
    mode: weather_entity_current
    entity_id: weather.local_station
```

Tryby:
- `entity`;
- `weather_entity_current`;
- `manual`;
- `derived`;
- `disabled`.

Model:

```python
@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    parameter: WeatherParameter
    start_at: datetime
    end_at: datetime
    value: float | str | bool
    unit: str | None
    source_mode: ObservationSourceMode
    source_entity_id: str | None
    quality: ObservationQuality
    entered_at: datetime
    metadata: Mapping[str, JSONValue]
```

Jakość:
- measured_precise;
- measured_approximate;
- manual_observation;
- estimated;
- derived.

### Ręczny deszcz

Panel i akcja muszą obsługiwać:
- brak;
- śladowy;
- lekki;
- umiarkowany;
- silny;
- dokładną wartość mm.

Kategoria nie może być automatycznie zamieniana w dokładną liczbę mm.

Akcja:

```yaml
action: forecast_fusion.record_observation
data:
  parameter: precipitation_occurrence
  start: "2026-07-22T15:00:00+02:00"
  end: "2026-07-22T16:00:00+02:00"
  value: true
  quality: manual_observation
```

---

## 9. Dopasowanie i weryfikacja

Proces:
1. pobierz zakończoną obserwację;
2. znajdź prognozy dotyczące tego czasu;
3. odrzuć prognozy pobrane po obserwowanym okresie;
4. przypisz lead-time bucket;
5. oblicz metryki;
6. zapisz idempotentny wynik;
7. zaktualizuj agregaty.

Horyzonty są konfigurowalne:

```yaml
lead_time_buckets:
  - id: 0_3h
    minimum_minutes: 0
    maximum_minutes: 180
  - id: 3_12h
    minimum_minutes: 180
    maximum_minutes: 720
  - id: 12_24h
    minimum_minutes: 720
    maximum_minutes: 1440
```

Zakaz nakładania przedziałów.

### Metryki
Temperatura/wiatr/wilgotność:
- MAE;
- bias;
- mediana błędu;
- RMSE opcjonalnie;
- sample count.

Prawdopodobieństwo opadu:
- Brier score;
- reliability bins;
- hit rate;
- false alarm;
- miss rate.

Ilość opadu:
- MAE;
- bias;
- osobno zdarzenia suche i mokre;
- błąd kategorii przy obserwacji jakościowej.

Condition:
- macierz pomyłek;
- balanced accuracy.

Stabilność:
```text
stability_delta = abs(new_forecast - previous_forecast)
```

Korzyść korekty:
```text
correction_benefit =
abs(previous_forecast - observation)
- abs(new_forecast - observation)
```

Stabilność i trafność są zawsze prezentowane osobno.

Status próby:
- `<10`: insufficient_data;
- `10..29`: provisional;
- `>=30`: established;
z możliwością konfiguracji.

---

## 10. Scoring źródeł

Scoring jest osobny dla:

```text
source × parameter × lead-time bucket × location/profile
```

W przyszłości możliwe sezon i regime pogodowy.

Efektywna waga:

```text
effective_weight =
quality_weight
× sample_confidence
× freshness
× source_health
× availability
```

Wymagania:
- shrinkage przy małej próbie;
- waga początkowa użytkownika;
- suma znormalizowanych wag = 1;
- źródło bez wartości ma wagę 0;
- źródło niedziałające traci wagę;
- pełny breakdown dostępny diagnostycznie.

---

## 11. Forecast Fusion

### Zmienne ciągłe
Domyślnie ważona mediana. Dodatkowo implementować ważoną średnią do testów i porównań.

### Opad
Model dwuetapowy:
1. prawdopodobieństwo wystąpienia;
2. ilość warunkowa na wystąpienie.

Wyjścia:
- precipitation_probability;
- expected_precipitation;
- conditional_precipitation_amount.

### Confidence

Uwzględnia:
- rozrzut źródeł;
- liczbę źródeł;
- efektywną liczbę źródeł;
- sample count;
- jakość historyczną;
- freshness;
- brakujące dane.

```python
@dataclass(frozen=True, slots=True)
class FusedValue:
    value: float | str | bool | None
    confidence: float
    lower_bound: float | None
    upper_bound: float | None
    contributing_sources: tuple[SourceContribution, ...]
    method: str
    reason_codes: tuple[str, ...]
```

Confidence musi być w `0..1`, ale nie może być opisywane jako dokładne prawdopodobieństwo poprawności bez kalibracji.

```python
@dataclass(frozen=True, slots=True)
class FusedForecastPoint:
    valid_at: datetime
    temperature: FusedValue
    apparent_temperature: FusedValue
    humidity: FusedValue
    precipitation_probability: FusedValue
    precipitation_amount: FusedValue
    wind_speed: FusedValue
    wind_gust: FusedValue
    cloud_cover: FusedValue
    condition: FusedValue
    overall_confidence: float
```

---

## 12. Okresy użytkownika

Typy:
- godzina;
- zakres godzin;
- zakres przez północ;
- cały dzień;
- cykliczny zakres dni tygodnia;
- godziny z `input_datetime`;
- ad hoc;
- kalendarz później.

```yaml
id: commute_to_work
name: Dojazd do pracy
schedule:
  mode: fixed
  days: [mon, tue, wed, thu, fri]
  start: "06:30"
  end: "07:30"
context:
  transport_entity_id: input_select.andrzej_dojazd_do_pracy
  activity_profile_id: commute
```

Agregaty:
- temperatura min/max/średnia;
- odczuwalna min;
- wiatr max i poryw max;
- prawdopodobieństwo deszczu max/średnie;
- oczekiwana suma;
- czas opadu;
- dominujący condition;
- confidence min/średnie;
- najgorszy podokres;
- najbardziej reprezentatywny podokres;
- największa zmiana od poprzedniej wersji.

Obowiązkowe testy DST.

---

## 13. Ubrania i zestawy

```python
@dataclass(frozen=True, slots=True)
class ClothingItem:
    item_id: str
    name: str
    category: ClothingCategory
    warmth_score: float
    wind_protection: float
    rain_protection: float
    breathability: float
    removable: bool
    active: bool
    allowed_activity_profiles: tuple[str, ...]
```

Kategorie:
upper_base, upper_mid, outer, lower, footwear, head, hands, neck, accessory.

```python
@dataclass(frozen=True, slots=True)
class Outfit:
    outfit_id: str
    name: str
    item_ids: tuple[str, ...]
    warmth_score: float
    wind_protection: float
    rain_protection: float
    breathability: float
    layer_count: int
    adjustable: bool
    active: bool
    allowed_contexts: tuple[str, ...]
```

Użytkownik może nadpisać automatycznie wyliczone parametry zestawu.

---

## 14. Profile kontekstu

```yaml
id: bicycle_commute
activity_intensity: 0.8
wind_exposure: 1.0
rain_sensitivity: 1.0
heat_generation: 0.8
cold_penalty: 1.2
heat_penalty: 1.0
```

Profil może być:
- stały;
- wybierany przez encję;
- wybierany przez szablon;
- automatyczny w późniejszym etapie.

Model zachowuje pełne cechy, nie tylko jedną „temperaturę efektywną”.

---

## 15. Feedback komfortu

```python
@dataclass(frozen=True, slots=True)
class ComfortFeedback:
    feedback_id: str
    user_profile_id: str
    start_at: datetime
    end_at: datetime
    period_id: str | None
    whole_day: bool

    recommended_outfit_id: str | None
    worn_outfit_id: str | None
    optimal_outfit_id: str | None

    comfort_score: int
    context_profile_id: str | None
    transport_value: str | None

    forecast_snapshot_id: str | None
    actual_weather_summary: WeatherSummary | None

    confidence: float
    note: str | None
    created_at: datetime
```

Skala `-3..+3`.

Feedback może dotyczyć:
- całego dnia;
- skonfigurowanego okresu;
- dowolnego zakresu;
- zestawu faktycznie użytego;
- zestawu uznanego za optymalny.

Zakresowy feedback ma większą wagę niż całodniowy.

Akcja:

```yaml
action: forecast_fusion.record_comfort_feedback
data:
  user_profile_id: andrzej
  start: "2026-07-22T06:30:00+02:00"
  end: "2026-07-22T07:30:00+02:00"
  comfort: slightly_warm
  worn_outfit_id: tshirt_hoodie
  optimal_outfit_id: tshirt
  period_id: commute_to_work
```

---

## 16. Uczenie granic komfortu

Model osobny dla:

```text
user × context × transport × outfit
```

Przechowuje:
- lower comfort boundary;
- upper comfort boundary;
- uncertainty;
- sample count;
- last update.

Aktualizacja ważoną średnią wykładniczą:

```text
new_boundary = old_boundary × (1 - alpha)
             + observed_condition × alpha
```

```text
alpha = base_alpha
      × feedback_confidence
      × context_similarity
      × age_weight
```

Wymagania:
- maksymalny krok jednej aktualizacji;
- decay starych danych;
- wyłączenie uczenia;
- reset;
- historia zmian;
- brak aktualizacji bez worn/optimal outfit;
- oddzielne transporty;
- feedback całodniowy z mniejszą wagą;
- LLM bez prawa modyfikacji modelu.

Predykcja:

```text
expected_discomfort =
cold_risk × cold_penalty
+ heat_risk × heat_penalty
+ rain_risk × rain_penalty
+ wind_risk × wind_penalty
+ adjustment_cost
```

Wynik zawiera reason codes.

---

## 17. Optymalizacja całego dnia

Strategie:
- minimize_total_discomfort;
- avoid_cold;
- avoid_heat;
- worst_period_first;
- longest_period_first;
- minimum_layers;
- maximum_adjustability.

```yaml
whole_day_strategy:
  method: minimize_total_discomfort
  cold_penalty: 1.5
  heat_penalty: 1.0
  rain_penalty: 1.2
  wind_penalty: 0.8
  outfit_change_penalty: 0.3
  prefer_removable_layers: true
```

Wynik:
- jeden zestaw bazowy;
- elementy do zabrania;
- instrukcje dla podokresów;
- alternatywa;
- confidence;
- wyjaśnienie.

---

## 18. Encje

Nie tworzyć automatycznie dziesiątek encji. Użytkownik używa kreatora outputów.

Platformy:
- weather;
- sensor;
- binary_sensor;
- opcjonalny select;
- opcjonalny button.

Przykłady:
- `weather.forecast_fusion_home`;
- sensor parametru dla godziny;
- sensor agregatu okresu;
- sensor rekomendacji;
- sensor confidence;
- binary sensor umbrella recommended;
- binary sensor significant change;
- sensor best source.

Definicja:

```python
@dataclass(frozen=True, slots=True)
class OutputDefinition:
    output_id: str
    platform: str
    name: str
    unique_id: str
    enabled: bool
    period_id: str | None
    value_path: str
    unit: str | None
    device_class: str | None
    state_class: str | None
    template: str | None
    attributes: Mapping[str, str]
```

Zmiana nazwy nie zmienia `unique_id`.

Encje diagnostyczne domyślnie disabled.

---

## 19. Szablony

Tryby:
- prosty placeholder;
- Jinja;
- preview;
- walidacja przed zapisem.

Przykładowy kontekst:

```jinja2
{{ period.name }}
{{ period.start }}
{{ forecast.temperature.min }}
{{ forecast.temperature.max }}
{{ forecast.precipitation.probability_max }}
{{ forecast.wind.gust_max }}
{{ forecast.confidence }}
{{ outfit.name }}
{{ outfit.items | join(", ") }}
{{ outfit.explanation }}
{{ sources.best_temperature }}
```

Błędny szablon:
- nie zatrzymuje coordinatora;
- powoduje unavailable tylko odpowiedniego outputu;
- tworzy diagnostyczny reason;
- nie ujawnia sekretów.

---

## 20. Akcje

Minimalne:
- `forecast_fusion.refresh`;
- `forecast_fusion.record_observation`;
- `forecast_fusion.record_comfort_feedback`;
- `forecast_fusion.recalculate`;
- `forecast_fusion.cleanup`;
- `forecast_fusion.export_data`;
- `forecast_fusion.generate_ai_analysis`.

Wszystkie rejestrowane w `async_setup`, opisane w `services.yaml`, tłumaczeniach i README.

---

## 21. Zdarzenia

Opcjonalne:
- forecast_fusion_forecast_updated;
- forecast_fusion_significant_change;
- forecast_fusion_feedback_recorded;
- forecast_fusion_model_updated;
- forecast_fusion_source_unhealthy;
- forecast_fusion_recommendation_changed.

Payload mały i stabilny.

---

## 22. AI

Providerzy:
- disabled;
- HA Conversation Agent;
- OpenAI-compatible;
- OpenAI;
- Ollama przez API zgodne z OpenAI.

AI może:
- generować opis;
- porównywać okresy;
- wskazywać anomalie;
- tłumaczyć niepewność;
- sugerować zmianę konfiguracji wymagającą potwierdzenia.

AI nie może:
- zmieniać wag;
- zmieniać progów;
- zapisywać obserwacji jako faktu;
- zastępować rekomendacji deterministycznej;
- być wymagane.

Odpowiedź strukturyzowana:

```json
{
  "summary": "string",
  "warnings": ["string"],
  "explanations": ["string"],
  "suggestions": [
    {
      "type": "configuration_change",
      "description": "string",
      "requires_confirmation": true
    }
  ]
}
```

Timeout, limit promptu, limit odpowiedzi, schema validation, fallback.

---

## 23. Storage

Konfiguracja i małe dane mogą używać `Store`. Duża historia ma korzystać z lokalnego SQLite lub repozytorium zoptymalizowanego do zapytań.

Interfejsy:

```python
class ForecastRepository(Protocol):
    async def save_snapshot(...)
    async def query_snapshots(...)
    async def delete_before(...)

class ObservationRepository(Protocol): ...
class FeedbackRepository(Protocol): ...
class StatisticsRepository(Protocol): ...
```

Wymagania:
- wersjonowany schema;
- idempotentne migracje;
- backup przed destrukcyjną migracją;
- rollback;
- indeksy po source, valid_at, parameter, bucket;
- transakcje;
- brak jednego wielkiego stale przepisywanego JSON;
- eksport bez sekretów.

---

## 24. Struktura repozytorium

```text
custom_components/forecast_fusion/
├── __init__.py
├── manifest.json
├── const.py
├── config_flow.py
├── coordinator.py
├── entity.py
├── diagnostics.py
├── repairs.py
├── services.yaml
├── weather.py
├── sensor.py
├── binary_sensor.py
├── select.py
├── button.py
├── translations/
│   ├── en.json
│   └── pl.json
├── api/
│   ├── websocket.py
│   └── schemas.py
├── core/
│   ├── models.py
│   ├── enums.py
│   ├── normalizer.py
│   ├── verifier.py
│   ├── metrics.py
│   ├── scoring.py
│   ├── fusion.py
│   ├── uncertainty.py
│   ├── periods.py
│   ├── clothing.py
│   ├── comfort.py
│   ├── learning.py
│   ├── templates.py
│   └── ai_analysis.py
├── repositories/
│   ├── base.py
│   ├── storage.py
│   ├── sqlite.py
│   └── migrations.py
└── managers/
    ├── source_manager.py
    ├── observation_manager.py
    ├── output_manager.py
    ├── retention_manager.py
    └── feedback_manager.py
```

---

## 25. Config flow

Pierwsza konfiguracja:
1. nazwa;
2. encje weather;
3. typ forecast;
4. test pobrania;
5. interwał;
6. podstawowe parametry;
7. obserwacje;
8. retencja;
9. zapis.

Nie wymagać ubrań podczas pierwszej konfiguracji.

Options:
- sources;
- polling;
- observations;
- scoring;
- buckets;
- retention;
- periods;
- user profiles;
- clothing;
- outputs;
- templates;
- AI;
- diagnostics.

Reconfigure nie usuwa historii. Zmiana entity ID domyślnie tworzy nowe logiczne źródło.

Walidacja:
- co najmniej jedno źródło;
- brak duplikatów;
- test action;
- typ forecast;
- jednostki;
- buckets;
- retention;
- templates;
- AI endpoint.

---

## 26. Diagnostyka i repairs

Diagnostyka:
- wersja;
- schema;
- liczba źródeł;
- health;
- interwały;
- liczby rekordów;
- zakres danych;
- statystyki błędów;
- config bez sekretów.

Nie zawiera:
- API keys;
- pełnych notatek;
- pełnych odpowiedzi AI;
- pełnej historii komfortu.

Repairs:
- brak źródeł;
- długotrwały błąd źródła;
- nieobsługiwany typ;
- uszkodzony storage;
- błąd migracji;
- trwały błąd template;
- zła observation entity.

---

## 27. Wydajność

- brak blokowania event loop;
- jeden poll obsługuje wszystkie encje;
- przyrostowy scoring;
- pełne przeliczenie wyłącznie jawnie;
- batch retention;
- brak dużych atrybutów encji;
- deduplikacja snapshotów;
- cache fused forecast;
- typowy profil: 5 źródeł, 30 min, 72 h hourly, 90 dni historii.

---

## 28. Bezpieczeństwo

- walidacja wszystkich action inputs;
- limity długości i zakresów;
- path traversal protection;
- brak wykonywania kodu;
- SSL verification domyślnie;
- maskowanie credentials;
- timeout AI;
- schema validation AI;
- brak pobierania URL z odpowiedzi modelu;
- brak sekretów w logach i diagnostyce.

---

# 29. Strategia testów

## 29.1. Standard
- pytest;
- pytest-homeassistant-custom-component;
- pytest-cov;
- ruff;
- mypy/pyright;
- hassfest;
- HACS validation;
- hypothesis opcjonalnie.

Pokrycie:
- całość minimum 90%;
- normalizer, metrics, scoring, fusion, learning minimum 95%;
- config flow pełne pokrycie gałęzi;
- każdy bug ma test regresyjny;
- zero real network calls.

## 29.2. Normalizacja
Testy:
- kompletne i niepełne dane;
- jednostki metric/imperial;
- UTC i offset;
- brak timezone;
- NaN/inf;
- wartości poza zakresem;
- wiatr ujemny/360/720;
- duplikaty;
- nieposortowane punkty;
- forecast pusty;
- unknown condition;
- hash identyczny i zmieniony;
- brak issued_at.

## 29.3. Pobieranie/coordinator
- jeden i wiele source;
- partial response;
- unavailable;
- unsupported type;
- timeout;
- action error;
- duplicate snapshot;
- changed snapshot;
- manual refresh;
- concurrent refresh;
- interval change;
- unload podczas fetch;
- reload;
- failed first refresh.

## 29.4. Metryki
- MAE/bias zero, dodatni, ujemny;
- wagi observation quality;
- Brier: 0/100/50;
- values out of range;
- stability bez previous;
- correction benefit dodatni/ujemny/zero.

## 29.5. Scoring
- equal sources;
- better source;
- small versus large sample;
- source health zero;
- missing parameter;
- stale forecast;
- initial weight;
- provisional status;
- normalization;
- all weights zero;
- single available source;
- changed buckets.

## 29.6. Fusion
- weighted median odd/even;
- outlier;
- one/no sources;
- None values;
- equal/dominant weights;
- input order invariance;
- result within source range;
- confidence vs disagreement;
- confidence one source;
- precipitation two-stage;
- missing history.

Property tests:
- permutation invariant;
- duplicate source with split weight invariant;
- confidence in 0..1;
- continuous result in min/max;
- increasing extreme weight cannot move result opposite direction.

## 29.7. Czas i okresy
- hourly;
- whole day;
- crossing midnight;
- DST spring;
- DST autumn;
- missing boundary point;
- partial/no coverage;
- irregular spacing;
- input_datetime;
- timezone;
- weekdays;
- disabled period;
- precipitation aggregation;
- confidence aggregation;
- worst period.

## 29.8. Obserwacje
- numeric, boolean, text;
- supported/unsupported units;
- unknown/unavailable;
- manual;
- overlap;
- correction;
- deletion;
- quality levels;
- categorical rain;
- exact rain;
- idempotent verification.

## 29.9. Learning
- no history;
- first feedback;
- cold moves lower boundary;
- warm moves upper boundary;
- comfortable reduces uncertainty;
- max step;
- decreasing alpha;
- low confidence;
- aged feedback;
- transport isolation;
- outfit isolation;
- whole-day lower weight;
- range higher weight;
- reset;
- disabled learning;
- missing worn outfit;
- optimal differs from worn;
- outlier;
- model confidence growth.

Properties:
- boundaries ordered;
- no NaN;
- max update bounded;
- user isolation;
- disabled means unchanged.

## 29.10. Outfit optimizer
- one/many outfits;
- avoid cold/heat;
- rain/wind;
- bicycle/car/walk;
- whole-day extremes;
- removable layers;
- invalid context outfit;
- deterministic tie;
- low confidence;
- no user history;
- alternate recommendation;
- recommendation changes after feedback.

## 29.11. Encje
- stable unique IDs;
- entity naming;
- availability;
- units/device/state class;
- attribute size;
- diagnostic disabled;
- no per-entity polling;
- delete output;
- rename output;
- invalid template.

## 29.12. Config flow
- success;
- abort;
- no entities;
- duplicate;
- unavailable;
- unsupported forecast;
- test fetch error;
- invalid interval;
- invalid retention;
- invalid observation;
- invalid template;
- reconfigure;
- options;
- reload;
- migration;
- translations.

## 29.13. Storage/migrations
- empty;
- read/write/restart;
- corrupt record;
- corrupt DB;
- concurrent writes;
- rollback;
- every migration;
- repeated migration;
- no space;
- retention/dry-run;
- export;
- redaction;
- large dataset.

## 29.14. AI
- disabled;
- timeout;
- 401/429/500;
- invalid JSON;
- too large;
- valid schema;
- no model mutation;
- no secret in logs;
- bounded context;
- deterministic fallback.

## 29.15. Security/diagnostics
- API key redaction;
- credentials redaction;
- no notes;
- size limit;
- path traversal;
- invalid service values;
- huge date range;
- huge note;
- malicious template;
- unload removes tasks/listeners.

---

## 30. Komendy jakości

```bash
python -m pytest -q
python -m pytest --cov=custom_components/forecast_fusion --cov-report=term-missing
ruff check .
ruff format --check .
mypy custom_components/forecast_fusion
python -m script.hassfest
```

CI:
1. lint;
2. format;
3. type check;
4. unit;
5. integration;
6. coverage;
7. Hassfest;
8. HACS validation;
9. release smoke test.

---

## 31. Etapy realizacji

### Etap 0 — szkielet
Manifest, config flow, coordinator, translations, CI, setup/unload tests.

### Etap 1 — prognozy
weather.get_forecasts, normalizacja, deduplikacja, storage, retencja, health.

### Etap 2 — obserwacje i scoring
encje observation, manual input, verifier, MAE, bias, Brier, buckets.

### Etap 3 — fusion
wagi, shrinkage, weighted median, rain model, confidence.

### Etap 4 — periods i outputs
period definitions, aggregation, output builder, entities, templates.

### Etap 5 — comfort
clothing, outfits, profiles, feedback, thresholds, optimizer.

### Etap 6 — panel
WebSocket API, overview, sources, observations, comfort, settings.

### Etap 7 — AI
provider abstraction, bounded context, structured response, fallback.

### Etap 8 — stabilizacja
diagnostics, repairs, export, migrations, performance, docs, beta, 1.0.

---

## 32. Kryteria ukończenia MVP

- [ ] UI config flow;
- [ ] minimum dwa weather sources;
- [ ] weather.get_forecasts;
- [ ] user polling interval;
- [ ] persistent history;
- [ ] configurable retention;
- [ ] independent temperature/rain observations;
- [ ] manual rain;
- [ ] scoring per horizon;
- [ ] fusion per parameter;
- [ ] confidence and contributions;
- [ ] custom period;
- [ ] selectable outputs;
- [ ] placeholder template;
- [ ] feedback with time, comfort, worn and optimal outfit;
- [ ] bounded threshold update;
- [ ] whole-day recommendation;
- [ ] source failure isolation;
- [ ] clean unload;
- [ ] full config flow coverage;
- [ ] critical modules >=95%;
- [ ] complete docs;
- [ ] no secrets in logs/diagnostics.

---

## 33. Oficjalne źródła do weryfikacji przed kodowaniem

- https://www.home-assistant.io/actions/weather.get_forecasts/
- https://developers.home-assistant.io/docs/creating_integration_file_structure/
- https://developers.home-assistant.io/docs/core/integration/config_flow/
- https://developers.home-assistant.io/docs/config_entries_index/
- https://developers.home-assistant.io/docs/integration_fetching_data/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/
- https://developers.home-assistant.io/docs/internationalization/custom_integration/
- https://openai.com/index/introducing-the-codex-app/

Przed każdą większą fazą sprawdzić aktualną dokumentację, ponieważ API i zalecenia Home Assistant mogą się zmieniać.
