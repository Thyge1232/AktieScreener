# Teknisk Oversigt over Investment Screener

Dette dokument er hovedindgangen til den tekniske dokumentation for Investment Screener-projektet. Formålet er at give et højniveau-overblik over systemets arkitektur og henvise til de detaljerede dokumenter for hver kernekomponent.

## Systemarkitektur

Applikationen er bygget op omkring en trelagsarkitektur:

1.  **UI Lag (Præsentation):** Håndteres af Streamlit. Dette lag inkluderer hoved-applikationen (`app.py`), de enkelte sider (`pages/`), og de interaktive UI-komponenter (`utils/aggrid_helpers.py`). Dets primære ansvar er at vise data og fange brugerinput.

2.  **Forretningslogik Lag (Kerne):** Dette er applikationens hjerne. Det indeholder de komplekse algoritmer for screening (`core/screening/`) og værdiansættelse (`core/valuation/`). Dette lag er uafhængigt af UI'et og modtager data, behandler det og returnerer et resultat.

3.  **Data Lag:** Håndterer al dataindhentning og -behandling. Det er opdelt i to dele:
    *   **Statisk Data:** Indlæsning og rensning af den indledende Finviz CSV-fil (`core/data/csv_processor.py`).
    *   **Dynamisk Data:** Hentning af live og historisk data fra eksterne API'er (`core/data/api_client.py`).

Disse lag er bundet sammen af konfigurationsfiler (`config/`) og et centraliseret state management-system (`st.session_state`).

## Indholdsfortegnelse

For en dybdegående forståelse af hver komponent, se venligst de følgende dokumenter:

*   **[1. Konfiguration og Dataloading](./01_CONFIG_AND_DATA_LOADING.md):** Forklarer, hvordan screeningsprofiler er defineret i JSON, og hvordan den indledende CSV-fil bliver indlæst og renset.
*   **[2. API Klient](./02_API_CLIENT.md):** Detaljerer, hvordan applikationen kommunikerer med Alpha Vantage, håndterer rate limits og bruger caching for at optimere ydeevnen.
*   **[3. Screenings-motor](./03_SCREENING_ENGINE.md):** En dybdegående gennemgang af point-beregning, vægtning og den kritiske sektor-normaliseringsalgoritme.
*   **[4. Værdiansættelses-motor](./04_VALUATION_ENGINE.md):** Forklarer den finansielle modellering bag DCF-analysen, WACC-beregning og scenarieanalyse.
*   **[5. UI Implementering](./05_UI_IMPLEMENTATION.md):** Beskriver, hvordan Streamlit bruges til navigation, state management og integration med interaktive AgGrid-tabeller.
*   **[6. Værktøjer og Hjælpefunktioner](./06_UTILITIES.md):** Dækker de understøttende moduler for validering, favoritstyring og mere.