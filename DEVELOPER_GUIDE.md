# 👩‍💻 Udviklerguide til Investment Screener

Velkommen, udvikler! Dette dokument giver et overblik over projektets arkitektur, de centrale designprincipper og fungerer som din primære indgang til den dybdegående tekniske dokumentation.

## 1. Projektstruktur

Projektet er bygget op omkring en klar og modulær struktur, der adskiller UI, forretningslogik og datahåndtering.

```
.
├── .streamlit/
│   └── secrets.toml                # API nøgler og hemmeligheder
├── config/
│   ├── mappings/
│   │   └── region_mappings.json    # Definition af geografiske regioner
│   └── strategies/
│       ├── value_screener_profiles.json
│       └── multibagger_profiles.json # Kerne-logik for screeningsstrategier
├── core/
│   ├── data/                       # Datahåndtering og API-integration
│   │   ├── client.py               # Central API-klient (Alpha Vantage, yfinance)
│   │   ├── caching.py              # SQLite-baseret caching-lag
│   │   ├── rate_limiter.py         # Rate limiting med backoff
│   │   ├── validators.py           # Validering af API-data
│   │   ├── config.py               # Dataklasser for konfiguration
│   │   └── csv_processor.py        # Indlæsning og rensning af Finviz CSV
│   ├── screening/                  # Screening-logik
│   │   ├── value_screener.py       # Orkestrator for value-screening
│   │   ├── multibagger_screener.py # Orkestrator for multibagger-screening
│   │   └── utils.py                # Kerne-evalueringsfunktioner og normalisering
│   ├── valuation/                  # Værdiansættelsesmoduler
│   │   └── ...                     # (DCF, WACC, Risk, etc.)
│   └── favorites_manager.py        # Håndtering af favorites.txt
├── pages/                          # Streamlit UI-sider
│   ├── value_screener.py
│   ├── multibagger_screener.py
│   ├── favorites.py
│   └── valuation.py
├── utils/                          # Genbrugelige UI-hjælpefunktioner
│   ├── aggrid_helpers.py           # JavaScript-kode til AgGrid
│   └── validation.py               # Validering af CSV-data og sikker UI-rendering
├── app.py                          # Hovedapplikation (entrypoint og router)
└── config_loader.py                # Indlæsning af JSON-konfigurationsfiler
```

## 2. Kernekoncepter

Vores arkitektur er baseret på et par vigtige designprincipper:

*   **Konfigurationsdrevet Design:** Næsten al screeningslogik (regler, point, vægte) er defineret i JSON-filer i `config/`-mappen. **For dig som udvikler betyder det, at du kan justere eller tilføje nye screeningskriterier primært ved at redigere JSON, ikke Python-kode.**

*   **Sektor-Normalisering:** For at sikre en fair sammenligning af nøgletal på tværs af brancher, anvender vi en normaliserings-algoritme, der vurderer hver aktie relativt til dens konkurrenter i samme sektor. **Dette sker i `core/screening/utils.py` og aktiveres via `normalization`-nøglen i JSON-profilerne.**

*   **Modulær Værdiansættelse:** Værdiansættelses-motoren (`core/valuation/`) er en selvstændig komponent, der udfører en komplet fundamental analyse. **Den er designet til at kunne fungere uafhængigt og kan i princippet genbruges i andre applikationer.**

*   **Robust Datahåndtering:** Al ekstern datakommunikation sker gennem en centraliseret API-klient (`core/data/client.py`), der implementerer aggressiv caching og en fallback-mekanisme. **Dette betyder, at UI-laget aldrig kalder direkte på et API, men altid går gennem klienten.**

## 3. Workflow for en Typisk Ændring

Forestil dig, at du vil tilføje et nyt screeningskriterie, "Price to Book Ratio (P/B)", til en value-profil.

1.  **Data Verifikation:** Sikr dig, at `P/B`-kolonnen er tilgængelig i din Finviz CSV-eksport. Hvis ikke, skal den tilføjes i Finviz, før du eksporterer.
2.  **Konfiguration:** Åbn `config/strategies/value_screener_profiles.json`. Find den relevante profil (f.eks., "Kvalitet (Quality Value)") og tilføj et nyt filter-objekt under `filters`:
    ```json
    "pb_ratio_scaled": {
      "data_key": "P/B",
      "type": "scaled",
      "description": "Pris i forhold til bogført værdi. Lavere er generelt billigere.",
      "min_value": 0.2,
      "max_value": 1.5,
      "target_min": 15,
      "target_max": 0
    }
    ```
3.  **Test:** Genstart Streamlit-applikationen. Det nye kriterie vil nu automatisk blive inkluderet i screeningen. Hvis du har aktiveret "Avanceret tilstand", vil en ny slider for "P/B" også blive vist.

Hvis det nye kriterie krævede en helt ny type beregning (f.eks. en logaritmisk skala), ville du tilføje en ny `evaluate_log_scaled_filter`-funktion i `core/screening/utils.py` og sætte `"type": "log_scaled"` i JSON-filen.

## 4. Dybdegående Teknisk Dokumentation

For en detaljeret, teknisk gennemgang af implementeringen af hvert enkelt kernemodul – inklusiv specifikke algoritmer, klasse-interaktioner og designvalg – henvises til vores fulde tekniske dokumentationsbibliotek:

*   **[Teknisk Oversigt](./docs/00_OVERVIEW.md)**
*   **[1. Konfiguration og Dataloading](./docs/01_CONFIG_AND_DATA_LOADING.md)**
*   **[2. API Klient](./docs/02_API_CLIENT.md)**
*   **[3. Screenings-motor](./docs/03_SCREENING_ENGINE.md)**
*   **[4. Værdiansættelses-motor](./docs/04_VALUATION_ENGINE.md)**
*   **[5. UI Implementering](./docs/05_UI_IMPLEMENTATION.md)**
*   **[6. Værktøjer og Hjælpefunktioner](./docs/06_UTILITIES.md)**

## 5. Kom Godt i Gang

For at opsætte projektet på din lokale maskine og køre det, følg venligst installationsguiden:

*   **[Installationsguide](./INSTALLATION.md)**