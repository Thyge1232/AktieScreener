# 2. API Klient

Modulet `core/data/api_client.py` er det eneste sted i applikationen, der kommunikerer med eksterne data-API'er. Det fungerer som et abstraktionslag, der skjuler kompleksiteten ved API-kald, caching og fejlhåndtering.

## Designprincipper

*   **Centralisering:** Al API-logik er samlet her. Hvis Alpha Vantage ændrer deres API, skal ændringerne kun laves i denne fil.
*   **Effektivitet:** Aggressiv brug af caching for at minimere API-kald, hvilket er afgørende for både ydeevne og for ikke at overskride grænserne for gratis API-nøgler.
*   **Robusthed:** Indbygget fallback-logik og omhyggelig fejlhåndtering for at sikre, at applikationen ikke går ned på grund af netværksproblemer eller API-fejl.

## Implementeringsdetaljer

*   **Caching (`@st.cache_data(ttl=...)`):**
    -   Hver funktion, der laver et API-kald, er dekoreret med Streamlits cache.
    -   `ttl` (Time To Live) er sat i sekunder. For eksempel betyder `ttl=600`, at resultatet af et API-kald gemmes i 10 minutter. Ethvert identisk kald inden for disse 10 minutter vil returnere det gemte resultat øjeblikkeligt uden at kontakte API'en. Dette er især vigtigt for `get_fundamental_data`.

*   **Rate Limiting:**
    -   Alpha Vantages gratis API har en streng grænse (typisk 5 kald/minut). I funktioner, der itererer over en liste af tickers (f.eks. `get_portfolio_historical_data`), er der en indbygget `time.sleep(12)` (eller mere). Dette er en bevidst pause, der sikrer, at applikationen holder sig under grænsen.
    -   Derudover tjekkes API-svaret for fejlmeddelelser, der indeholder "api call frequency", og der vises en `st.error` til brugeren.

*   **Fallback-mekanisme (`get_fundamental_data`):**
    -   Funktionen er pakket ind i en `try...except`-blok.
    -   **Første forsøg:** Den kalder Alpha Vantages `OVERVIEW` endpoint.
    -   **Fallback:** Hvis det første forsøg fejler (enten pga. en netværksfejl, en ugyldig ticker, eller hvis Alpha Vantage returnerer tomme data), fanges fejlen. `except`-blokken aktiverer så `yfinance`-biblioteket for at hente de samme data. Den returnerer en dictionary, der er struktureret til at ligne Alpha Vantages output for at sikre konsistens.

*   **Data-strukturering:**
    -   Funktionerne returnerer veldefinerede datastrukturer. `get_daily_prices` returnerer en pænt formateret Pandas DataFrame med omdøbte kolonner og et `datetime`-indeks. `get_fundamental_data` returnerer en dictionary. Dette gør det forudsigeligt for resten af applikationen at arbejde med dataen.