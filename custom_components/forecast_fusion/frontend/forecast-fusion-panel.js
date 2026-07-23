class ForecastFusionPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.activeTab = 'forecast';
    this.data = null;
    this.historyData = null;
    this.hass = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.data) {
      this.fetchData();
    }
  }

  get hass() {
    return this._hass;
  }

  async fetchData() {
    if (!this._hass) return;
    try {
      // Fetch overview data
      const configEntries = Object.values(this._hass.configEntries || {});
      const fusionEntry = configEntries.find(e => e.domain === 'forecast_fusion');
      const entryId = fusionEntry ? fusionEntry.entry_id : '';

      if (entryId) {
        this.entryId = entryId;
        const res = await this._hass.callWS({
          type: 'forecast_fusion/get_overview',
          config_entry_id: entryId
        });
        this.data = res;

        const hist = await this._hass.callWS({
          type: 'forecast_fusion/get_history',
          config_entry_id: entryId
        });
        this.historyData = hist;
      }
    } catch (e) {
      console.error('Error fetching Forecast Fusion data:', e);
    }
    this.render();
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 16px;
          background: var(--primary-background-color, #111827);
          color: var(--primary-text-color, #f3f4f6);
          font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
          min-height: 100vh;
          box-sizing: border-box;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: rgba(31, 41, 55, 0.7);
          backdrop-filter: blur(10px);
          padding: 16px 24px;
          border-radius: 12px;
          margin-bottom: 20px;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        h1 {
          margin: 0;
          font-size: 1.5rem;
          color: #3b82f6;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .btn {
          background: #2563eb;
          color: #fff;
          border: none;
          padding: 8px 16px;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 500;
          transition: background 0.2s;
        }
        .btn:hover {
          background: #1d4ed8;
        }
        .tabs {
          display: flex;
          gap: 8px;
          margin-bottom: 20px;
        }
        .tab-btn {
          padding: 10px 18px;
          background: #1f2937;
          border: 1px solid rgba(255, 255, 255, 0.05);
          color: #9ca3af;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 500;
        }
        .tab-btn.active {
          background: #3b82f6;
          color: #fff;
          border-color: #3b82f6;
        }
        .card {
          background: #1f2937;
          border-radius: 12px;
          padding: 20px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          margin-bottom: 20px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 10px;
        }
        th, td {
          text-align: left;
          padding: 12px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        th {
          color: #9ca3af;
          font-weight: 500;
        }
        .badge {
          background: #059669;
          color: #ecfdf5;
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 0.85rem;
        }
        .form-group {
          margin-bottom: 16px;
        }
        label {
          display: block;
          margin-bottom: 6px;
          color: #d1d5db;
        }
        input, select {
          width: 100%;
          padding: 10px;
          background: #111827;
          border: 1px solid #374151;
          color: #fff;
          border-radius: 6px;
          box-sizing: border-box;
        }
      </style>

      <div class="header">
        <h1>🌤 Forecast Fusion & Personal Comfort</h1>
        <button class="btn" id="refresh-btn">🔄 Odśwież Dane</button>
      </div>

      <div class="tabs">
        <button class="tab-btn ${this.activeTab === 'forecast' ? 'active' : ''}" id="tab-forecast">Prognozy i Fusion</button>
        <button class="tab-btn ${this.activeTab === 'history' ? 'active' : ''}" id="tab-history">Dane Historyczne</button>
        <button class="tab-btn ${this.activeTab === 'feedback' ? 'active' : ''}" id="tab-feedback">Ocena i Feedback</button>
        <button class="tab-btn ${this.activeTab === 'sensors' ? 'active' : ''}" id="tab-sensors">Czujniki Weryfikujące</button>
      </div>

      <div id="tab-content">
        ${this.renderActiveTab()}
      </div>
    `;

    this.shadowRoot.getElementById('refresh-btn').addEventListener('click', () => this.fetchData());
    this.shadowRoot.getElementById('tab-forecast').addEventListener('click', () => { this.activeTab = 'forecast'; this.render(); });
    this.shadowRoot.getElementById('tab-history').addEventListener('click', () => { this.activeTab = 'history'; this.render(); });
    this.shadowRoot.getElementById('tab-feedback').addEventListener('click', () => { this.activeTab = 'feedback'; this.render(); });
    this.shadowRoot.getElementById('tab-sensors').addEventListener('click', () => { this.activeTab = 'sensors'; this.render(); });

    if (this.activeTab === 'feedback') {
      const fbForm = this.shadowRoot.getElementById('feedback-form');
      if (fbForm) {
        fbForm.addEventListener('submit', (e) => this.handleFeedbackSubmit(e));
      }
    }
    if (this.activeTab === 'sensors') {
      const sensForm = this.shadowRoot.getElementById('sensors-form');
      if (sensForm) {
        sensForm.addEventListener('submit', (e) => this.handleSensorsSubmit(e));
      }
    }
  }

  renderActiveTab() {
    if (this.activeTab === 'forecast') {
      return this.renderForecastTab();
    } else if (this.activeTab === 'history') {
      return this.renderHistoryTab();
    } else if (this.activeTab === 'feedback') {
      return this.renderFeedbackTab();
    } else if (this.activeTab === 'sensors') {
      return this.renderSensorsTab();
    }
  }

  renderForecastTab() {
    if (!this.data) {
      return `<div class="card"><p>Ładowanie danych prognoz...</p></div>`;
    }

    const points = this.data.fused_points || [];
    const sources = this.data.sources || [];
    const algo = this.data.fusion_algorithm || 'weighted_median';
    const conf = Math.round((this.data.overall_confidence || 1.0) * 100);

    return `
      <div class="card">
        <h3>Podsumowanie Fuzji Pogody</h3>
        <p><strong>Algorytm Fuzji:</strong> ${algo} | <strong>Ogólna Pewność:</strong> <span class="badge">${conf}%</span></p>
        <p><strong>Aktywne Źródła Prognoz (${sources.length}):</strong> ${sources.join(', ')}</p>
      </div>

      <div class="card">
        <h3>Połączone Prognozy Godzinowe</h3>
        <table>
          <thead>
            <tr>
              <th>Godzina</th>
              <th>Temperatura</th>
              <th>Odczuwalna</th>
              <th>Wilgotność</th>
              <th>Szansa Opadu</th>
              <th>Opad (mm)</th>
              <th>Wiatr (m/s)</th>
              <th>Warunki</th>
              <th>Pewność</th>
            </tr>
          </thead>
          <tbody>
            ${points.map(p => `
              <tr>
                <td>${new Date(p.valid_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                <td>${p.temperature !== null ? p.temperature + '°C' : '-'}</td>
                <td>${p.apparent_temperature !== null ? p.apparent_temperature + '°C' : '-'}</td>
                <td>${p.humidity !== null ? p.humidity + '%' : '-'}</td>
                <td>${p.precipitation_probability !== null ? p.precipitation_probability + '%' : '-'}</td>
                <td>${p.precipitation_amount !== null ? p.precipitation_amount + ' mm' : '-'}</td>
                <td>${p.wind_speed !== null ? p.wind_speed + ' m/s' : '-'}</td>
                <td>${p.condition || '-'}</td>
                <td><span class="badge">${Math.round(p.overall_confidence * 100)}%</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  renderHistoryTab() {
    const obs = this.historyData ? this.historyData.recent_observations || [] : [];
    return `
      <div class="card">
        <h3>Dane Historyczne i Obserwacje Weryfikacyjne (${obs.length})</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Parametr</th>
              <th>Zakres Czasu</th>
              <th>Wartość Obserwowana</th>
              <th>Tryb Źródła</th>
            </tr>
          </thead>
          <tbody>
            ${obs.length > 0 ? obs.map(o => `
              <tr>
                <td>${o.id}</td>
                <td>${o.parameter}</td>
                <td>${new Date(o.start_at).toLocaleString()} - ${new Date(o.end_at).toLocaleTimeString()}</td>
                <td><strong>${o.value}</strong></td>
                <td>${o.source_mode} (${o.source_entity_id || 'manual'})</td>
              </tr>
            `).join('') : `<tr><td colspan="5">Brak zapisanych obserwacji weryfikacyjnych.</td></tr>`}
          </tbody>
        </table>
      </div>
    `;
  }

  renderFeedbackTab() {
    const now = new Date();
    const isoNow = now.toISOString().slice(0, 16);

    return `
      <div class="card">
        <h3>Ustawienie Oceny Komfortu / Obserwacji Pogodowej</h3>
        <p>Wprowadź subiektywną ocenę komfortu lub obserwację opadów na konkretną godzinę, zakres godzin lub cały dzień.</p>
        <form id="feedback-form">
          <div class="form-group">
            <label>ID Użytkownika:</label>
            <input type="text" id="fb-user" value="default_user" required>
          </div>
          <div class="form-group">
            <label>Czas Początkowy:</label>
            <input type="datetime-local" id="fb-start" value="${isoNow}" required>
          </div>
          <div class="form-group">
            <label>Czas Końcowy:</label>
            <input type="datetime-local" id="fb-end" value="${isoNow}" required>
          </div>
          <div class="form-group">
            <label>Ocena Komfortu Termicznego (-3 Zimno, 0 Idealnie, +3 Gorąco):</label>
            <select id="fb-score">
              <option value="-3">-3 (Bardzo zimno)</option>
              <option value="-2">-2 (Zimno)</option>
              <option value="-1">-1 (Lekko chłodno)</option>
              <option value="0" selected>0 (Idealnie / Komfortowo)</option>
              <option value="1">+1 (Lekko ciepło)</option>
              <option value="2">+2 (Ciepło / Gorąco)</option>
              <option value="3">+3 (Bardzo gorąco)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Obserwacja Opadów (opcjonalnie):</label>
            <select id="fb-rain">
              <option value="">Brak wpisu</option>
              <option value="none">Brak opadów</option>
              <option value="drizzle">Mżawka</option>
              <option value="rain">Lekki/Średni Deszcz</option>
              <option value="heavy_rain">Ulewa</option>
            </select>
          </div>
          <button class="btn" type="submit">Zapisz Ocenę</button>
        </form>
      </div>
    `;
  }

  renderSensorsTab() {
    const vSensors = this.data ? this.data.verification_sensors || {} : {};
    return `
      <div class="card">
        <h3>Ustawienie Czujników "Prawdziwej Pogody" do Weryfikacji</h3>
        <p>Przypisz stacje pogodowe lub czujniki fizyczne zainstalowane w Home Assistant do automatycznej weryfikacji prognoz.</p>
        <form id="sensors-form">
          <div class="form-group">
            <label>Czujnik Temperatury (np. sensor.temp_zewnetrzna):</label>
            <input type="text" id="sens-temp" value="${vSensors.temperature || ''}" placeholder="sensor.outdoor_temperature">
          </div>
          <div class="form-group">
            <label>Czujnik Wilgotności (np. sensor.wilgotnosc_zewnetrzna):</label>
            <input type="text" id="sens-hum" value="${vSensors.humidity || ''}" placeholder="sensor.outdoor_humidity">
          </div>
          <div class="form-group">
            <label>Czujnik Opadu / Deszczomierz (np. sensor.deszczomierz):</label>
            <input type="text" id="sens-precip" value="${vSensors.precipitation || ''}" placeholder="sensor.rain_gauge">
          </div>
          <div class="form-group">
            <label>Czujnik Prędkości Wiatru (np. sensor.anemometr):</label>
            <input type="text" id="sens-wind" value="${vSensors.wind_speed || ''}" placeholder="sensor.wind_speed">
          </div>
          <button class="btn" type="submit">Zapisz Czujniki Weryfikujące</button>
        </form>
      </div>
    `;
  }

  async handleFeedbackSubmit(e) {
    e.preventDefault();
    if (!this._hass || !this.entryId) return;

    const user = this.shadowRoot.getElementById('fb-user').value;
    const start = new Date(this.shadowRoot.getElementById('fb-start').value).toISOString();
    const end = new Date(this.shadowRoot.getElementById('fb-end').value).toISOString();
    const score = parseInt(this.shadowRoot.getElementById('fb-score').value, 10);
    const rain = this.shadowRoot.getElementById('fb-rain').value;

    try {
      await this._hass.callWS({
        type: 'forecast_fusion/submit_feedback',
        config_entry_id: this.entryId,
        user_profile_id: user,
        start_at: start,
        end_at: end,
        comfort_score: score,
        manual_rain_observation: rain || undefined
      });
      alert('Ocena komfortu została pomyślnie zapisana!');
      this.fetchData();
    } catch (err) {
      alert('Błąd podczas zapisywania oceny: ' + err.message);
    }
  }

  async handleSensorsSubmit(e) {
    e.preventDefault();
    if (!this._hass || !this.entryId) return;

    const vSensors = {
      temperature: this.shadowRoot.getElementById('sens-temp').value || undefined,
      humidity: this.shadowRoot.getElementById('sens-hum').value || undefined,
      precipitation: this.shadowRoot.getElementById('sens-precip').value || undefined,
      wind_speed: this.shadowRoot.getElementById('sens-wind').value || undefined
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
