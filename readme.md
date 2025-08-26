# 📊 Investment Screener


**Investment Screener** er en web-applikation bygget med Streamlit, designet til at analysere og screene aktier baseret på data fra Finviz. Applikationen giver investorer mulighed for at finde potentielle investeringer ved hjælp af to primære strategier: **Value Investing** og **Multibagger (Vækst) Investing**.

Værktøjet er bygget til at være interaktivt og fleksibelt, så brugeren kan tilpasse screeningskriterier, gemme favoritaktier til videre analyse og endda udføre dybdegående værdiansættelser.

## Nøglefunktioner

*   **Dobbelt Screeningsmodul:** Vælg mellem en Value Screener, der finder undervurderede selskaber, og en Multibagger Finder, der leder efter selskaber med højt vækstpotentiale.
*   **Fleksible Screeningsprofiler:** Hver screener er drevet af JSON-konfigurationsfiler, som definerer forudindstillede strategier (f.eks. "Kvalitet & Værdi").
*   **Dynamisk Vægtjustering:** I "Avanceret tilstand" kan du justere vægten af hvert enkelt finansielt nøgletal for at skræddersy screeningen til din egen strategi.
*   **Sektor-Normaliseret Scoring:** For at sikre en fair sammenligning mellem selskaber i forskellige brancher (f.eks. en bank vs. en tech-virksomhed), normaliseres nøgletal inden for deres respektive sektorer.
*   **Favoritstyring:** Gem interessante aktier fra dine screeninger til en central favoritliste, som gemmes i en `favorites.txt`-fil mellem sessioner.
*   **Dybdegående Værdiansættelse:** Favoritsiden henter live kursdata og kan udføre en avanceret **DCF-baseret værdiansættelse** (Discounted Cash Flow), komplet med WACC-beregning og scenarieanalyse (Best/Base/Worst Case).
*   **Interaktive Tabeller:** Alle resultater præsenteres i interaktive tabeller, hvor du kan sortere, filtrere, tilføje/fjerne favoritter og klikke dig direkte videre til Finviz.
*   **Robust Datavalidering:** Systemet tjekker automatisk, om den uploadede CSV-fil indeholder de nødvendige kolonner for den valgte screeningsprofil, og advarer om potentielle datakvalitetsproblemer.

## Teknologistak

*   **Frontend:** [Streamlit](https://streamlit.io/)
*   **Dataanalyse:** [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
*   **Interaktive Tabeller:** [streamlit-aggrid](https://github.com/PablocFonseca/streamlit-aggrid)
*   **Datavisualisering:** [Plotly](https://plotly.com/python/)
*   **Ekstern Data:** [yfinance](https://github.com/ranaroussi/yfinance) (som fallback for API-data)

## Hurtig Start

1.  **Klon Repositoriet:**
    ```bash
    git clone <din-repository-url>
    cd <repository-mappe>
    ```

2.  **Installer Afhængigheder:**
    Opret en `requirements.txt` fil og installer de nødvendige pakker.
    ```bash
    # requirements.txt
    streamlit
    pandas
    numpy
    plotly
    streamlit-aggrid
<<<<<<< HEAD
    yfinance  
=======
    yfinance
>>>>>>> ff8234e9f2e4e33f3a08729290b9480581869560

    # Kommando i terminalen
    pip install -r requirements.txt
    ```

3.  **Konfigurer API Nøgle (Valgfrit, men anbefalet):**
    For at bruge værdiansættelse- og backtesting-funktionerne skal du have en gratis API-nøgle fra [Alpha Vantage](https://www.alphavantage.co/). Opret en fil her: `.streamlit/secrets.toml` og tilføj din nøgle:
    ```toml
    # .streamlit/secrets.toml
    ALPHA_VANTAGE_API_KEY = "DIN_API_NØGLE_HER"
    ```

4.  **Opret Konfigurationsfiler:**
    Opret følgende mappestruktur og placer dine JSON-konfigurationsfiler der:
    ```
    config/
    ├── mappings/
    │   └── region_mappings.json
    └── strategies/
        ├── value_screener_profiles.json
        └── multibagger_profiles.json
    ```

5.  **Tilføj Data:**
    Download en CSV-fil med aktiedata fra Finviz.com og placer den i roden af projektmappen. Applikationen indlæser den automatisk ved start.

6.  **Kør Applikationen:**
    ```bash
    streamlit run app.py
    ```
    Åbn den URL, der vises i din terminal, i en browser for at starte screeneren.
