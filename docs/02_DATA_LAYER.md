
# Projektdokumentation: Financial Data Layer

## 1. Overordnet Projektdokumentation

### Projektoversigt

*   **Formål:** At levere et robust og effektivt datalag til en finansiel analyseapplikation. Modulet håndterer al kommunikation med eksterne finansielle API'er og abstraherer kompleksiteten vedrørende dataindhentning, caching, rate limiting og validering.
*   **Anvendelsesområde:** Fungerer som backend-dataservice for et Streamlit-baseret finansielt dashboard, der kræver realtids- og historiske aktiedata.
*   **Teknologistak:** Python 3.9+, Streamlit, Requests, Pandas, yfinance.

## 2. Dokumentation pr. Fil

### `core/data/config.py`

*   **Formål:** Centraliserer al statisk konfiguration for datalaget for at sikre nem vedligeholdelse og justering.
*   **Nøglekomponenter:**
    *   **Klasse:** `AppConfig`
        *   En `dataclass`, der samler konfigurationsparametre i logiske grupper.
        *   `api_config`: Indeholder indstillinger som rate limits, timeouts og retry-strategier for hver ekstern API.
        *   `cache_config`: Definerer Time-To-Live (TTL) i sekunder for forskellige datatyper.
        *   `validation_ranges`: Specificerer acceptable numeriske intervaller for finansielle nøgletal.
    *   **Instans:** `config`
        *   En global instans af `AppConfig`, som importeres af andre moduler i datalaget.
*   **Afhængigheder:**
    *   **Interne Moduler:** Ingen.
    *   **Eksterne Biblioteker:** `dataclasses` (standardbibliotek).
*   **Eksempel på Anvendelse:**
    ```python
    from .config import config

    # Hent cache TTL for fundamental data
    ttl = config.cache_config.get('fundamental', 3600)
    ```

### `core/data/caching.py`

*   **Formål:** Implementerer en højtydende, persistent cache baseret på SQLite for at minimere API-kald og forbedre applikationens svartid.
*   **Nøglekomponenter:**
    *   **Klasse:** `SQLiteCache`
        *   `__init__(...)`: Initialiserer databaseforbindelsen og opretter de nødvendige tabeller og indekser.
        *   `get_cache_key(...)`: Genererer en unik SHA256-hash baseret på funktionsnavn og argumenter.
        *   `get_cached_result(...)`: Henter et valideret (ikke-udløbet) resultat fra cachen. Inkrementerer `access_count` ved cache hit.
        *   `save_to_cache(...)`: Serialiserer og gemmer et resultat i databasen med metadata som TTL, størrelse og datatype.
        *   `_maybe_cleanup()`: Kører periodisk for at fjerne udløbne poster og trimme cachen, hvis den overstiger en defineret størrelse.
*   **Afhængigheder:**
    *   **Interne Moduler:** `core.data.config`.
    *   **Eksterne Biblioteker:** `sqlite3`, `hashlib`, `json`, `threading`, `logging`.
*   **Eksempel på Anvendelse:**
    ```python
    from .caching import SQLiteCache

    smart_cache = SQLiteCache()
    # Gemmer data i cachen
    smart_cache.save_to_cache(result={'price': 150}, func_name='get_price', data_type='live_price', ticker='AAPL')
    ```

### `core/data/rate_limiter.py`

*   **Formål:** Håndterer API rate limiting intelligent med dynamisk backoff for at undgå at overskride brugsgrænser og håndtere midlertidige API-fejl.
*   **Nøglekomponenter:**
    *   **Klasse:** `EnhancedRateLimiter`
        *   `wait_if_needed(...)`: Hovedmetode, der blokerer eksekvering, hvis antallet af kald inden for det seneste minut overskrider grænsen. Viser en spinner i UI.
        *   `register_failure(...)`: Kaldes, når et API-kald fejler. Implementerer en eksponentiel backoff-strategi ved at sætte en `backoff_until` tidsstempel.
        *   `register_success()`: Nulstiller fejl-tælleren og backoff-perioden efter et succesfuldt kald.
        *   `get_stats()`: Returnerer statistik om performance, herunder succesrate og nuværende backoff-status.
*   **Afhængigheder:**
    *   **Interne Moduler:** Ingen.
    *   **Eksterne Biblioteker:** `time`, `threading`, `logging`, `streamlit`.

### `core/data/validators.py`

*   **Formål:** Leverer robuste funktioner til validering, rensning og sikker konvertering af finansielle data.
*   **Nøglekomponenter:**
    *   **Klasse:** `AdvancedDataValidator`
        *   `validate_financial_data(...)`: Validerer en dictionary af finansielle data mod foruddefinerede intervaller fra `config.py`. Udfører også krydsvalidering mellem relaterede nøgletal (f.eks. P/E, EPS, Market Cap).
        *   `safe_numeric(...)`: En meget robust funktion til at konvertere strenge (f.eks. "1.5B", "50%", "N/A") til `float`. Returnerer `None` ved fejl.
*   **Afhængigheder:**
    *   **Interne Moduler:** `core.data.config`.
    *   **Eksterne Biblioteker:** `pandas`, `numpy`.
*   **Eksempel på Anvendelse:**
    ```python
    from .validators import AdvancedDataValidator

    raw_data = {'PERatio': '1500', 'MarketCapitalization': '2.1T'}
    cleaned_data, warnings = AdvancedDataValidator.validate_financial_data(raw_data, 'AAPL')
    # `warnings` vil indeholde en besked om, at P/E er uden for det acceptable interval.
    ```

### `core/data/csv_processor.py`

*   **Formål:** Håndterer indlæsning, parsing og behandling af bruger-uploadede CSV-filer, specifikt formateret som eksport fra Finviz.
*   **Nøglekomponenter:**
    *   **Funktion:** `process_finviz_csv(file_or_path, cache_key)`
        *   Dekoreret med `@st.cache_data` for at undgå genbehandling af den samme fil.
        *   Renser kolonnenavne og fjerner ugyldige rækker.
        *   Anvender hjælpefunktioner til at konvertere strenge (f.eks. "Market Cap") og procenter til numeriske typer.
        *   Beregner afledte nøgletal som `Price vs. Book/sh`.
    *   **Funktion:** `parse_market_cap(market_cap_str)`
        *   Hjælpefunktion, der konverterer strenge som "500M" (millioner), "2.5B" (milliarder) og "1.1T" (trillioner) til et float.
*   **Afhængigheder:**
    *   **Interne Moduler:** Ingen.
    *   **Eksterne Biblioteker:** `pandas`, `numpy`, `streamlit`.

### `core/data/client.py`

*   **Formål:** Fungerer som det centrale orkestreringsmodul og den primære grænseflade for dataindhentning. Kombinerer caching, rate limiting og validering.
*   **Nøglekomponenter:**
    *   **Funktioner:** `get_live_price`, `get_fundamental_data`, `get_daily_prices`
        *   Hovedfunktioner til at hente specifikke datatyper for en given ticker.
        *   Implementerer en fallback-strategi: forsøger først med Alpha Vantage, og hvis det fejler, bruges `yfinance` som backup.
    *   **Decorator:** `@with_intelligent_cache_and_limits(data_type: str)`
        *   En custom decorator, der elegant kombinerer caching (`smart_cache.get_cached_result`) og rate limiting (`alpha_vantage_limiter.wait_if_needed`) for alle API-kaldsfunktioner.
    *   **Batch Processing:** `get_portfolio_data_batch(...)`
        *   Bruger `ThreadPoolExecutor` til at hente data for flere tickers parallelt, hvilket markant forbedrer ydeevnen.
    *   **Monitoring:** `PerformanceMonitor` klasse og `get_api_health_check` funktion
        *   Samler metrikker om API-kalds performance og leverer et samlet sundhedstjek, der kan vises i UI.
*   **Afhængigheder:**
    *   **Interne Moduler:** `caching`, `rate_limiter`, `validators`, `config`.
    *   **Eksterne Biblioteker:** `requests`, `pandas`, `streamlit`, `yfinance` (valgfri).
*   **Eksempel på Anvendelse:**
    ```python
    from .client import get_fundamental_data

    # Henter fundamental data for Apple Inc.
    # Caching, rate limiting og fallback håndteres automatisk.
    response = get_fundamental_data(ticker='AAPL')

    if response.success:
        print(response.data)
    ```

## 3. Projektstruktur og Relationer

### Mappestruktur

Projektets datalag er organiseret i en flad, modulær struktur under `core/data/`, hvor hver fil har et klart defineret ansvarsområde.

```
core/
└── data/
    ├── __init__.py
    ├── client.py          # Orkestrator og offentlig grænseflade
    ├── caching.py         # SQLite cache-logik
    ├── config.py          # Statisk konfiguration
    ├── csv_processor.py   # Logik for CSV-filer
    ├── rate_limiter.py    # API rate limit-logik
    └── validators.py      # Datavalidering og -rensning
```

### Arkitektonisk Overblik

Systemet er designet omkring `client.py` som det centrale adgangspunkt. De andre moduler fungerer som specialiserede "hjælpere", der leverer specifik funktionalitet.

Dataflowet for et typisk API-kald (f.eks. `get_fundamental_data('AAPL')`) er som følger:

1.  **Kald:** UI eller en anden service kalder en funktion i `client.py`.
2.  **Decorator:** Decoratoren `@with_intelligent_cache_and_limits` aktiveres.
3.  **Cache Check:** Den kalder `caching.smart_cache.get_cached_result()` for at tjekke for et friskt, cachet resultat. Hvis det findes, returneres det med det samme.
4.  **Rate Limit:** Hvis der ikke er et cache hit, kaldes `rate_limiter.alpha_vantage_limiter.wait_if_needed()`. Hvis API'en er overbelastet, pauser tråden her.
5.  **API Kald:** `client.py` udfører selve HTTP-kaldet til Alpha Vantage API'en.
6.  **Fallback:** Hvis Alpha Vantage-kaldet fejler, forsøges et nyt kald med `yfinance` som backup.
7.  **Validering:** Det modtagne JSON-svar sendes til `validators.AdvancedDataValidator.validate_financial_data()` for rensning og validering.
8.  **Caching:** Det rensede resultat gemmes i cachen via `caching.smart_cache.save_to_cache()`.
9.  **Retur:** Det endelige, validerede resultat pakkes i et `APIResponse`-objekt og returneres til kalderen.

Alle moduler henter deres konfigurationsparametre (f.eks. cache-varighed, API-grænser, valideringsintervaller) fra den centrale `config.py`-fil.