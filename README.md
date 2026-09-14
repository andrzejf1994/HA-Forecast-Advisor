# Forecast Fusion & Personal Comfort for Home Assistant

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/andrzejf1994/HA-Forecast-Advisor)](https://github.com/andrzejf1994/HA-Forecast-Advisor/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Forecast Fusion & Personal Comfort** is an advanced Home Assistant integration that aggregates multiple weather forecast sources using robust statistical fusion algorithms (Weighted Median, Two-Stage Precipitation Model) and learns personal comfort boundaries for outfit recommendations.

---

## 🌟 Key Features

* **Multi-Source Fusion Engine**: Combines multiple weather entities into a single high-accuracy fused forecast.
* **Weighted Median & Mean Algorithms**: Outlier-resistant fusion models that prevent single bad weather providers from skewing forecasts.
* **Two-Stage Precipitation Model**: Separates rain occurrence probability from expected precipitation amounts.
* **Dynamic Uncertainty & Confidence Scoring**: Calculates $N_{\text{eff}}$ (effective source count) and weighted variance confidence metrics.
* **Personal Comfort Boundary Learning**: Learns individual thermal comfort limits per user, transport method, and outfit using bounded exponential moving average updates.
* **Time Period & DST-Safe Aggregation**: DST-safe morning/commute period forecast summaries.
* **Privacy-Safe AI Advice**: Optional natural language weather advice generation with bounded context and credential redaction.

---

## 🚀 Installation

### Option 1: Via HACS (Recommended)

1. Open **HACS** in your Home Assistant instance.
2. Click on **Integrations** -> **Custom Repositories** (top right menu).
3. Add Repository URL: `https://github.com/andrzejf1994/HA-Forecast-Advisor`.
4. Category: **Integration**.
5. Click **Download** and restart Home Assistant.

### Option 2: Manual Installation

1. Copy the `custom_components/forecast_fusion` directory to your Home Assistant's `custom_components` folder.
2. Restart Home Assistant.

---

## ⚙️ Configuration

1. In Home Assistant, navigate to **Settings** -> **Devices & Services**.
2. Click **Add Integration** and search for **Forecast Fusion**.
3. Select your source weather entities (e.g. `weather.met_no`, `weather.openweather`).
4. Set your preferred polling interval and complete the setup.

---

## 📊 Services

* `forecast_fusion.refresh`: Trigger an immediate forecast fetch from all configured sources.
* `forecast_fusion.recalculate`: Recalculate historical accuracy metrics and fusion weights.
* `forecast_fusion.record_observation`: Record a ground truth weather observation.
* `forecast_fusion.record_comfort_feedback`: Log user comfort feedback for outfit learning.
* `forecast_fusion.cleanup`: Run retention data cleanup manually.
* `forecast_fusion.export_data`: Export anonymous verification and comfort statistics.
* `forecast_fusion.generate_ai_analysis`: Synthesize natural language weather advice.

---

## 🛠️ Sidebar troubleshooting

The sidebar loads the current fused forecast independently from historical data.
If the SQLite history database is temporarily busy during a refresh or reload,
the current forecast remains available and the history view retries on the next
panel refresh.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
