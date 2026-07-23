class ForecastFusionPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.activeTab = 'forecast';
    this.timeMode = 'hour'; // 'hour' | 'day' | 'range'
    this.data = null;
    this.historyData = null;
    this.hass = null;
    this.loading = true;
    this.errorMsg = null;
  }

  set hass(hass) {
    const isFirstInit = !this._hass;
    this._hass = hass;
    if (isFirstInit) {
      this.fetchData();
    }
  }

  get hass() {
    return this._hass;
  }

  async fetchData() {
    if (!this._hass) return;
    this.loading = true;
    this.errorMsg = null;
    this.render();

    try {
      // Fetch overview data directly via WS API (backend automatically resolves active entry)
      const res = await this._hass.callWS({
        type: 'forecast_fusion/get_overview'
      });
      this.data = res;
      if (res && res.config_entry_id) {
        this.entryId = res.config_entry_id;
      }

      // Fetch history data
      try {
        const hist = await this._hass.callWS({
          type: 'forecast_fusion/get_history',
          config_entry_id: this.entryId
        });
        this.historyData = hist;
      } catch (hErr) {
        console.warn('Could not fetch history data:', hErr);
      }
    } catch (e) {
      console.error('Error fetching Forecast Fusion data:', e);
      this.errorMsg = 'Nie udało się pobrać danych z Forecast Fusion. Upewnij się, że integracja jest dodana i uruchomiona w Home Assistant.';
    } finally {
      this.loading = false;
      this.render();
    }
  }

  get currentUserName() {
    if (this._hass && this._hass.user) {
      return this._hass.user.name || this._hass.user.id || 'default_user';
    }
    return 'default_user';
  }

  getCurrentFormattedHour() {
    const now = new Date();
    now.setMinutes(0, 0, 0);
    const tzOffset = now.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(now.getTime() - tzOffset)).toISOString().slice(0, 16);
    return localISOTime;
  }

  getCurrentFormattedDate() {
    const now = new Date();
    const tzOffset = now.getTimezoneOffset() * 60000;
    return (new Date(now.getTime() - tzOffset)).toISOString().slice(0, 10);
  }

  switchTab(tab) {
    this.activeTab = tab;
    this.render();
  }

  setTimeMode(mode) {
    this.timeMode = mode;
    this.render();
  }

  render() {
    const lastSuccess = this.data ? this.data.last_update_success : false;
    const points = (this.data && this.data.fused_points) ? this.data.fused_points : [];
    const sensors = (this.data && this.data.verification_sensors) ? this.data.verification_sensors : {};
    const historyObs = (this.historyData && this.historyData.recent_observations) ? this.historyData.recent_observations : [];
    const historyFused = (this.historyData && this.historyData.fused_points) ? this.historyData.fused_points : (this.data && this.data.fused_points ? this.data.fused_points : []);

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 24px;
          background: var(--primary-background-color, #0f172a);
          color: var(--primary-text-color, #f8fafc);
          font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          min-height: 100vh;
          box-sizing: border-box;
        }

        .header-container {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 24px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--divider-color, #334155);
        }

        .title-area h1 {
          margin: 0;
          font-size: 24px;
          font-weight: 700;
          background: linear-gradient(135deg, #38bdf8, #818cf8);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;

          display: flex;
          align-items: center;
          gap: 12px;
        }

        .subtitle {
          margin: 4px 0 0 0;
          font-size: 13px;
          color: #94a3b8;
        }

        .tab-bar {
          display: flex;
          gap: 8px;
          margin-bottom: 20px;
          background: #1e293b;
          padding: 6px;
          border-radius: 12px;
        }

        .tab-btn {
          flex: 1;
          padding: 10px 16px;
          border: none;
          background: transparent;
          color: #94a3b8;
          font-size: 14px;
          font-weight: 600;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .tab-btn:hover {
          color: #f8fafc;
          background: rgba(255, 255, 255, 0.05);
        }

        .tab-btn.active {
          background: #3b82f6;
          color: #ffffff;
          box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }

        .card {
          background: #1e293b;
          border: 1px solid #334155;
          border-radius: 16px;
          padding: 24px;
          margin-bottom: 20px;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }

        .card h2 {
          margin-top: 0;
          margin-bottom: 16px;
          font-size: 18px;
          font-weight: 600;
          color: #f1f5f9;
        }

        .table-responsive {
          overflow-x: auto;
        }

        table {
          width: 100%;
          border-collapse: collapse;
          text-align: left;
          font-size: 14px;
        }

        th {
          background: #0f172a;
          color: #94a3b8;
          padding: 12px;
          border-bottom: 2px solid #334155;
          font-weight: 600;
          text-transform: uppercase;
          font-size: 11px;
          letter-spacing: 0.5px;
        }

        td {
          padding: 12px;
          border-bottom: 1px solid #334155;
        }

        tr:hover td {
          background: rgba(255, 255, 255, 0.02);
        }

        .confidence-badge {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 700;
          background: rgba(59, 130, 246, 0.2);
          color: #60a5fa;
        }

        .status-pill {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 600;
        }

        .status-pill.success {
          background: rgba(34, 197, 94, 0.2);
          color: #4ade80;
        }

        .status-pill.error {
          background: rgba(239, 68, 68, 0.2);
          color: #f87171;
        }

        /* Form elements */
        .mode-selector {
          display: flex;
          gap: 8px;
          margin-bottom: 20px;
        }

        .mode-btn {
          padding: 8px 16px;
          border: 1px solid #334155;
          background: #0f172a;
          color: #94a3b8;
          border-radius: 8px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
          transition: all 0.2s;
        }

        .mode-btn.active {
          background: #3b82f6;
          color: #ffffff;
          border-color: #3b82f6;
        }

        .form-group {
          margin-bottom: 16px;
        }

        .form-group label {
          display: block;
          margin-bottom: 6px;
          font-size: 13px;
          font-weight: 600;
          color: #cbd5e1;
        }

        .form-control {
          width: 100%;
          padding: 10px 14px;
          border-radius: 8px;
          border: 1px solid #334155;
          background: #0f172a;
          color: #f8fafc;
          font-size: 14px;
          box-sizing: border-box;
        }

        .form-control:focus {
          outline: none;
          border-color: #3b82f6;
        }

        .grid-2 {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }

        .clothing-section {
          background: #0f172a;
          padding: 16px;
          border-radius: 12px;
          border: 1px solid #334155;
          margin-bottom: 20px;
        }

        .clothing-section h3 {
          margin-top: 0;
          font-size: 14px;
          color: #38bdf8;
          margin-bottom: 12px;
        }

        .btn-submit {
          background: linear-gradient(135deg, #3b82f6, #2563eb);
          color: #ffffff;
          border: none;
          padding: 12px 24px;
          font-size: 14px;
          font-weight: 700;
          border-radius: 8px;
          cursor: pointer;
          width: 100%;
          transition: transform 0.1s, box-shadow 0.2s;
        }

        .btn-submit:hover {
          box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
        }

        .btn-submit:active {
          transform: scale(0.99);
        }

        .loading-spinner {
          text-align: center;
          padding: 40px;
          color: #94a3b8;
        }

        .alert-error {
          background: rgba(239, 68, 68, 0.15);
          border: 1px solid rgba(239, 68, 68, 0.4);
          color: #fca5a5;
          padding: 14px;
          border-radius: 8px;
          margin-bottom: 20px;
        }
      </style>

      <div class="header-container">
        <div class="title-area">
          <h1><img src="/forecast_fusion_panel/icon.png" style="width:36px; height:36px; border-radius:8px; object-fit:cover; vertical-align:middle;"> Forecast Fusion & Personal Comfort</h1>
          <p class="subtitle">Inteligentna synteza prognoz pogodowych i uczenie preferencji termicznych</p>
        </div>
        <div>
          ${
            lastSuccess
              ? `<span class="status-pill success">● Połączono z modelem</span>`
              : `<span class="status-pill error">● Oczekiwanie na dane</span>`
          }
        </div>
      </div>

      <div class="tab-bar">
        <button class="tab-btn ${this.activeTab === 'forecast' ? 'active' : ''}" id="tab-forecast">
          📊 Prognozy i Fuzja
        </button>
        <button class="tab-btn ${this.activeTab === 'feedback' ? 'active' : ''}" id="tab-feedback">
          ✍️ Ocena i Ubiór
        </button>
        <button class="tab-btn ${this.activeTab === 'history' ? 'active' : ''}" id="tab-history">
          📜 Dane Historyczne
        </button>
        <button class="tab-btn ${this.activeTab === 'sensors' ? 'active' : ''}" id="tab-sensors">
          🌡️ Czujniki Weryfikujące
        </button>
      </div>

      ${this.errorMsg ? `<div class="alert-error">${this.errorMsg}</div>` : ''}

      ${
        this.loading
          ? `<div class="loading-spinner">⏳ Ładowanie danych z Forecast Fusion...</div>`
          : this.renderTabContent(points, sensors, historyObs, historyFused)
      }
    `;

    this.bindEvents();
  }

  renderTabContent(points, sensors, historyObs, historyFused) {
    if (this.activeTab === 'forecast') {
      return `
        <div class="card">
          <h2>Zagregowana Prognoza Pogody (Fusion Output)</h2>
          <p style="font-size: 13px; color: #94a3b8; margin-bottom: 16px;">
            Wynik fuzji z uwzględnieniem ważonej mediany oraz odporności na wartości odstające z ${
              this.data ? (this.data.sources || []).length : 0
            } źródeł pogodowych.
          </p>
          <div class="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Czas (Valid At)</th>
                  <th>Temp (°C)</th>
                  <th>Odczuwalna (°C)</th>
                  <th>Wilgotność (%)</th>
                  <th>Prawdop. Opadów (%)</th>
                  <th>Opad (mm)</th>
                  <th>Wiatr (km/h)</th>
                  <th>Pewność</th>
                </tr>
              </thead>
              <tbody>
                ${
                  points.length === 0
                    ? `<tr><td colspan="8" style="text-align:center; color:#94a3b8;">Brak dostępnych punktów prognozy</td></tr>`
                    : points.map(p => `
                        <tr>
                          <td><b>${new Date(p.valid_at).toLocaleString('pl-PL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</b></td>
                          <td style="color:#60a5fa; font-weight:700;">${p.temperature != null ? p.temperature.toFixed(1) : '-'}</td>
                          <td>${p.apparent_temperature != null ? p.apparent_temperature.toFixed(1) : '-'}</td>
                          <td>${p.humidity != null ? Math.round(p.humidity) : '-'}%</td>
                          <td>${p.precipitation_probability != null ? Math.round(p.precipitation_probability) : '-'}%</td>
                          <td style="color:#38bdf8;">${p.precipitation_amount != null ? p.precipitation_amount.toFixed(1) : '-'}</td>
                          <td>${p.wind_speed != null ? p.wind_speed.toFixed(1) : '-'}</td>
                          <td><span class="confidence-badge">${p.overall_confidence != null ? Math.round(p.overall_confidence * 100) : 0}%</span></td>
                        </tr>
                      `).join('')
                }
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    if (this.activeTab === 'feedback') {
      const defaultTime = this.getCurrentFormattedHour();
      const defaultDate = this.getCurrentFormattedDate();

      return `
        <div class="card">
          <h2>Zgłoszenie Odczucia Termicznego i Ubioru</h2>
          <p style="font-size: 13px; color: #94a3b8; margin-bottom: 20px;">
            Wprowadź swoje wrażenie cieplne oraz zaimplementowany ubiór. Model uczenia dostosuje granice komfortu dla Twojego profilu.
          </p>

          <form id="feedback-form" onsubmit="return false;">
            <div class="form-group">
              <label for="fb-user-id">ID / Profil Użytkownika Home Assistant:</label>
              <input type="text" id="fb-user-id" class="form-control" list="ha-users-list" value="${this.currentUserName}" placeholder="Wpisz lub wybierz użytkownika...">
              <datalist id="ha-users-list">
                <option value="${this.currentUserName}"></option>
                <option value="Domownik"></option>
                <option value="Gość"></option>
              </datalist>
            </div>

            <div class="form-group">
              <label>Zakres czasowy wpisu:</label>
              <div class="mode-selector">
                <button type="button" class="mode-btn ${this.timeMode === 'hour' ? 'active' : ''}" id="mode-hour">⏰ Godzina (Obecna)</button>
                <button type="button" class="mode-btn ${this.timeMode === 'day' ? 'active' : ''}" id="mode-day">📅 Cały Dzień</button>
                <button type="button" class="mode-btn ${this.timeMode === 'range' ? 'active' : ''}" id="mode-range">↔️ Custom Zakres</button>
              </div>
            </div>

            ${
              this.timeMode === 'hour'
                ? `
                  <div class="form-group">
                    <label for="fb-start-hour">Wybierz konkretną godzinę:</label>
                    <input type="datetime-local" id="fb-start-hour" class="form-control" value="${defaultTime}">
                  </div>
                `
                : this.timeMode === 'day'
                ? `
                  <div class="form-group">
                    <label for="fb-start-date">Wybierz dzień:</label>
                    <input type="date" id="fb-start-date" class="form-control" value="${defaultDate}">
                  </div>
                `
                : `
                  <div class="grid-2">
                    <div class="form-group">
                      <label for="fb-range-start">Czas początkowy:</label>
                      <input type="datetime-local" id="fb-range-start" class="form-control" value="${defaultTime}">
                    </div>
                    <div class="form-group">
                      <label for="fb-range-end">Czas końcowy:</label>
                      <input type="datetime-local" id="fb-range-end" class="form-control" value="${defaultTime}">
                    </div>
                  </div>
                `
            }

            <div class="form-group">
              <label for="fb-score">Ocena Komfortu Termicznego:</label>
              <select id="fb-score" class="form-control">
                <option value="-3">🥶 -3: BARDZO ZIMNO (Marznę)</option>
                <option value="-2">❄️ -2: ZIMNO</option>
                <option value="-1">🧊 -1: LEKKO CHŁODNO</option>
                <option value="0" selected>😊 0: KOMFORTOWO (Idealnie)</option>
                <option value="1">🌤️ +1: LEKKO CIEPŁO</option>
                <option value="2">🔥 +2: GORĄCO</option>
                <option value="3">🥵 +3: BARDZO GORĄCO (Pociłem się)</option>
              </select>
            </div>

            <!-- Sekcja Ubioru z osobnymi opcjami dla wiatrówki, płaszcza, kurtki przeciwdeszczowej i zimowej -->
            <div class="clothing-section">
              <h3>👔 Zastosowany Ubiór (Spodnie, Bluza, Kurtka)</h3>
              <div class="grid-2" style="grid-template-columns: 1fr 1fr 1fr;">
                <div class="form-group">
                  <label for="fb-pants">👖 Spodnie / Dół:</label>
                  <select id="fb-pants" class="form-control">
                    <option value="spodnie_krotkie">Krótkie spodenki / Spódnica</option>
                    <option value="spodnie_dlugie" selected>Długie spodnie / Dżinsy</option>
                    <option value="spodnie_dresowe">Dresy / Spodnie ocieplane</option>
                  </select>
                </div>
                <div class="form-group">
                  <label for="fb-top">🧥 Bluza / Sweter:</label>
                  <select id="fb-top" class="form-control">
                    <option value="bluza_brak">Brak (Sam T-Shirt / Koszulka)</option>
                    <option value="bluza_lekka" selected>Lekka bluza / Sweter</option>
                    <option value="bluza_gruba">Gruba bluza / Polar</option>
                  </select>
                </div>
                <div class="form-group">
                  <label for="fb-jacket">🧥 Kurtka / Odzież wierzchnia:</label>
                  <select id="fb-jacket" class="form-control">
                    <option value="kurtka_brak" selected>Brak kurtki</option>
                    <option value="wiatrowka">Wiatrówka</option>
                    <option value="plaszcz">Płaszcz</option>
                    <option value="kurtka_przeciwdeszczowa">Kurtka przeciwdeszczowa</option>
                    <option value="kurtka_zimowa">Kurtka zimowa</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="form-group">
              <label for="fb-rain">Obserwacja Opadu (Opcjonalna):</label>
              <select id="fb-rain" class="form-control">
                <option value="">Brak wpisu opadu</option>
                <option value="none">Brak deszczu (Sucho)</option>
                <option value="drizzle">Mżawka / Lekki deszcz</option>
                <option value="rain">Ulewa / Padający deszcz</option>
                <option value="snow">Śnieg</option>
              </select>
            </div>

            <button type="button" class="btn-submit" id="btn-save-feedback">💾 Zapisz Ocenę i Ubiór</button>
          </form>
        </div>
      `;
    }

    if (this.activeTab === 'history') {
      // Group observations and forecasts by time bucket
      const groupsMap = new Map();

      const getHourKey = (isoStr) => {
        if (!isoStr) return null;
        const d = new Date(isoStr);
        if (isNaN(d.getTime())) return null;
        d.setMinutes(0, 0, 0);
        return d.toISOString();
      };

      // 1. Group observations by time slot
      historyObs.forEach(o => {
        const key = getHourKey(o.start_at || o.end_at);
        if (!key) return;
        if (!groupsMap.has(key)) {
          groupsMap.set(key, {
            timeKey: key,
            startAt: o.start_at,
            endAt: o.end_at,
            obs: {},
            forecast: null
          });
        }
        const item = groupsMap.get(key);
        item.obs[o.parameter] = o.value;
      });

      // 2. Group fused forecasts by time slot
      historyFused.forEach(fp => {
        const key = getHourKey(fp.valid_at);
        if (!key) return;
        if (!groupsMap.has(key)) {
          groupsMap.set(key, {
            timeKey: key,
            startAt: fp.valid_at,
            endAt: fp.valid_at,
            obs: {},
            forecast: null
          });
        }
        const item = groupsMap.get(key);
        item.forecast = fp;
      });

      const groupedRows = Array.from(groupsMap.values()).sort((a, b) => new Date(b.timeKey) - new Date(a.timeKey));

      return `
        <div class="card">
          <h2>Dane Historyczne Pogody: Obserwacje Rzeczywiste vs Prognoza</h2>
          <p style="font-size: 13px; color: #94a3b8; margin-bottom: 20px;">
            Wiersze zgrupowane według zakresu czasu (godziny). Kolumny prezentują odczyty fizyczne czujników rzeczywistych obok wartości przewidywanych przez fuzję prognoz wraz z obliczoną różnicą (błędem).
          </p>
          <div class="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Zakres Czasu</th>
                  <th>Rzeczywista Temp (°C)</th>
                  <th>Rzeczywisty Opad</th>
                  <th>Rzeczywisty Wiatr (km/h)</th>
                  <th>Prognoza Temp (°C)</th>
                  <th>Prognoza Opad (mm)</th>
                  <th>Prognoza Wiatr (km/h)</th>
                  <th>Warunki Prognozy</th>
                  <th>Różnica Temp (°C)</th>
                </tr>
              </thead>
              <tbody>
                ${
                  groupedRows.length === 0
                    ? `<tr><td colspan="9" style="text-align:center; color:#94a3b8;">Brak zapisanych obserwacji ani prognoz dla zakresów czasu.</td></tr>`
                    : groupedRows.map(r => {
                        const obsTemp = r.obs.temperature != null ? parseFloat(r.obs.temperature) : null;
                        const obsPrecip = r.obs.precipitation != null ? r.obs.precipitation : '-';
                        const obsWind = r.obs.wind_speed != null ? parseFloat(r.obs.wind_speed) : null;

                        const fcTemp = r.forecast && r.forecast.temperature != null ? r.forecast.temperature : null;
                        const fcPrecip = r.forecast && r.forecast.precipitation_amount != null ? r.forecast.precipitation_amount : null;
                        const fcWind = r.forecast && r.forecast.wind_speed != null ? r.forecast.wind_speed : null;
                        const fcCond = r.forecast && r.forecast.condition ? r.forecast.condition : '-';

                        let tempDiff = '-';
                        if (obsTemp != null && fcTemp != null) {
                          const diff = (fcTemp - obsTemp).toFixed(1);
                          const sign = diff > 0 ? '+' : '';
                          tempDiff = `${sign}${diff}°C`;
                        }

                        return `
                          <tr>
                            <td><b>${new Date(r.timeKey).toLocaleString('pl-PL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</b></td>
                            <td style="color:#60a5fa; font-weight:700;">${obsTemp != null ? obsTemp.toFixed(1) : '-'}</td>
                            <td style="color:#38bdf8;">${obsPrecip}</td>
                            <td>${obsWind != null ? obsWind.toFixed(1) : '-'}</td>
                            <td style="color:#818cf8; font-weight:700;">${fcTemp != null ? fcTemp.toFixed(1) : '-'}</td>
                            <td style="color:#38bdf8;">${fcPrecip != null ? fcPrecip.toFixed(1) : '-'}</td>
                            <td>${fcWind != null ? fcWind.toFixed(1) : '-'}</td>
                            <td><span class="confidence-badge">${fcCond}</span></td>
                            <td style="font-weight:700; color:${tempDiff.startsWith('+') ? '#f87171' : tempDiff.startsWith('-') ? '#60a5fa' : '#94a3b8'}">${tempDiff}</td>
                          </tr>
                        `;
                      }).join('')
                }
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    if (this.activeTab === 'sensors') {
      return `
        <div class="card">
          <h2>Czujniki "Prawdziwej Pogody" (Verification Sensors)</h2>
          <p style="font-size: 13px; color: #94a3b8; margin-bottom: 20px;">
            Przypisz encje fizycznych czujników zamontowanych w Twoim domu/ogrodzie, aby automatycznie weryfikować dokładność dostawców pogodowych.
          </p>

          <form id="sensors-form" onsubmit="return false;">
            <div class="form-group">
              <label for="sens-temp">Czujnik Temperatury Rzeczywistej:</label>
              <input type="text" id="sens-temp" class="form-control" value="${sensors.temperature || ''}" placeholder="sensor.outdoor_temperature">
            </div>

            <div class="form-group">
              <label for="sens-hum">Czujnik Wilgotności Rzeczywistej:</label>
              <input type="text" id="sens-hum" class="form-control" value="${sensors.humidity || ''}" placeholder="sensor.outdoor_humidity">
            </div>

            <div class="form-group">
              <label for="sens-precip">Czujnik Opadów / Stacja Pogodowa:</label>
              <input type="text" id="sens-precip" class="form-control" value="${sensors.precipitation || ''}" placeholder="sensor.rain_gauge">
            </div>

            <div class="form-group">
              <label for="sens-wind">Czujnik Prędkości Wiatru:</label>
              <input type="text" id="sens-wind" class="form-control" value="${sensors.wind_speed || ''}" placeholder="sensor.wind_speed">
            </div>

            <button type="button" class="btn-submit" id="btn-save-sensors">💾 Zapisz Czujniki Weryfikujące</button>
          </form>
        </div>
      `;
    }

    return '';
  }

  bindEvents() {
    const root = this.shadowRoot;

    // Tab buttons
    const tForecast = root.getElementById('tab-forecast');
    const tFeedback = root.getElementById('tab-feedback');
    const tHistory = root.getElementById('tab-history');
    const tSensors = root.getElementById('tab-sensors');

    if (tForecast) tForecast.addEventListener('click', () => this.switchTab('forecast'));
    if (tFeedback) tFeedback.addEventListener('click', () => this.switchTab('feedback'));
    if (tHistory) tHistory.addEventListener('click', () => this.switchTab('history'));
    if (tSensors) tSensors.addEventListener('click', () => this.switchTab('sensors'));

    // Mode buttons in feedback
    const mHour = root.getElementById('mode-hour');
    const mDay = root.getElementById('mode-day');
    const mRange = root.getElementById('mode-range');

    if (mHour) mHour.addEventListener('click', () => this.setTimeMode('hour'));
    if (mDay) mDay.addEventListener('click', () => this.setTimeMode('day'));
    if (mRange) mRange.addEventListener('click', () => this.setTimeMode('range'));

    // Save Feedback button
    const btnFb = root.getElementById('btn-save-feedback');
    if (btnFb) {
      btnFb.addEventListener('click', () => this.submitFeedback());
    }

    // Save Sensors button
    const btnSens = root.getElementById('btn-save-sensors');
    if (btnSens) {
      btnSens.addEventListener('click', () => this.saveSensors());
    }
  }

  async submitFeedback() {
    const root = this.shadowRoot;
    const userId = root.getElementById('fb-user-id').value || this.currentUserName;
    const score = parseInt(root.getElementById('fb-score').value, 10);
    const rain = root.getElementById('fb-rain').value;

    const pants = root.getElementById('fb-pants').value;
    const top = root.getElementById('fb-top').value;
    const jacket = root.getElementById('fb-jacket').value;
    const outfitId = `${pants}+${top}+${jacket}`;

    let startIso, endIso, wholeDay = false;

    if (this.timeMode === 'hour') {
      const val = root.getElementById('fb-start-hour').value;
      const sDate = val ? new Date(val) : new Date();
      const eDate = new Date(sDate.getTime() + 3600000);
      startIso = sDate.toISOString();
      endIso = eDate.toISOString();
    } else if (this.timeMode === 'day') {
      const val = root.getElementById('fb-start-date').value;
      const sDate = val ? new Date(val + 'T00:00:00') : new Date();
      const eDate = new Date(sDate.getTime() + 86400000);
      startIso = sDate.toISOString();
      endIso = eDate.toISOString();
      wholeDay = true;
    } else {
      const sVal = root.getElementById('fb-range-start').value;
      const eVal = root.getElementById('fb-range-end').value;
      startIso = sVal ? new Date(sVal).toISOString() : new Date().toISOString();
      endIso = eVal ? new Date(eVal).toISOString() : new Date().toISOString();
    }

    try {
      await this._hass.callWS({
        type: 'forecast_fusion/submit_feedback',
        config_entry_id: this.entryId,
        user_profile_id: userId,
        start_at: startIso,
        end_at: endIso,
        comfort_score: score,
        whole_day: wholeDay,
        worn_outfit_id: outfitId,
        manual_rain_observation: rain || undefined
      });
      alert('Zapisano ocenę komfortu oraz dane ubioru!');
      this.fetchData();
    } catch (err) {
      alert('Błąd podczas zapisywania oceny: ' + err.message);
    }
  }

  async saveSensors() {
    const root = this.shadowRoot;

    const vSensors = {
      temperature: root.getElementById('sens-temp').value || undefined,
      humidity: root.getElementById('sens-hum').value || undefined,
      precipitation: root.getElementById('sens-precip').value || undefined,
      wind_speed: root.getElementById('sens-wind').value || undefined
    };

    try {
      await this._hass.callWS({
        type: 'forecast_fusion/save_verification_sensors',
        config_entry_id: this.entryId,
        verification_sensors: vSensors
      });
      alert('Ustawienia czujników weryfikujących zostały zapisane!');
      this.fetchData();
    } catch (err) {
      alert('Błąd podczas zapisywania czujników: ' + err.message);
    }
  }
}

customElements.define('forecast-fusion-panel', ForecastFusionPanel);
