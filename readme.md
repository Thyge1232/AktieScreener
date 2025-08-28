# 📊 Investment Screener

**Investment Screener** er en avanceret web-applikation bygget med Streamlit, designet til at analysere, screene og værdiansætte aktier baseret på data fra Finviz og eksterne finansielle API'er. Applikationen giver investorer et omfattende værktøj til at identificere potentielle investeringer gennem to primære strategier: **Value Investing** og **Multibagger (Vækst) Investing**.

Værktøjet kombinerer en kraftfuld backend-motor med et interaktivt interface, så brugeren kan tilpasse screeningskriterier, administrere en favoritliste og udføre dybdegående, fundamental værdiansættelse.

## 🚀 Nøglefunktioner

*   **Dobbelt Screeningsmodul:** Vælg mellem en Value Screener, der finder undervurderede selskaber baseret på traditionelle værdinøgletal, og en Multibagger Finder, der fokuserer på vækstmetrikker for at finde fremtidige winners.
*   **Konfigurationsdrevne Strategier:** Hver screener styres af JSON-konfigurationsfiler (`value_screener_profiles.json`, `multibagger_profiles.json`), som definerer forudindstillede, justerbare strategier (f.eks. "Deep Value" eller "Kvalitet & Værdi").
*   **Dynamisk Vægtjustering:** I "Avanceret tilstand" kan brugeren justere indflydelsen (vægten) af hvert enkelt finansielt nøgletal for at skræddersy screeningen til en personlig investeringsfilosofi.
*   **Avanceret Sektor-Normalisering:** Løser problemet med at sammenligne æbler og appelsiner. Motoren normaliserer nøgletal (f.eks. P/E) inden for deres respektive sektorer vha. `SectorNormalizer`-klassen, hvilket sikrer en fair rangering af en tech-virksomhed mod en bank.
*   **Omfattende Værdiansættelsesmotor:** Udfører fundamental værdiansættelse (`ComprehensiveValuationEngine`) baseret på Discounted Cash Flow (DCF), sammenlignelige multipla (P/E, EV/EBITDA, P/B) og en detaljeret risikovurdering. Inkluderer scenarie- og sensitivitetsanalyse for at vurdere usikkerhed.
*   **Intelligent Caching & Rate Limiting:** Backenden håndterer datahentning fra API'er intelligent med caching i SQLite og dynamisk rate limiting for at optimere performance og overholde API-grænser.
*   **Robust Datavalidering & Håndtering:** Systemet validerer automatisk uploadede CSV-filer og API-svar for at sikre datakvalitet og forhindre applikationsfejl.
*   **Interaktive AgGrid-tabeller:** Alle resultater vises i højt tilpasselige tabeller med JavaScript-integration, der muliggør direkte links til Finviz, visning af favoritstjerner og professionel formatering af finansielle tal.
*   **Session-Persistent Favoritliste:** Brugeren kan gemme interessante aktier på tværs af sessioner i en simpel filbaseret favoritliste.

## 🛠️ Teknologistak

*   **Frontend & App Framework:** [Streamlit](https://streamlit.io/)
*   **Datahåndtering & Analyse:** [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
*   **Interaktive Tabeller:** [streamlit-aggrid](https://github.com/PablocFonseca/streamlit-aggrid)
*   **Datavisualisering:** [Plotly](https://plotly.com/python/) (i værdiansættelsesmodulet)
*   **Ekstern Data & API-kommunikation:** [Requests](https://docs.python-requests.org/), [yfinance](https://github.com/ranaroussi/yfinance) (som fallback)
*   **Caching:** SQLite (via `sqlite3` standardbiblioteket)
*   **Konfiguration & Serialisering:** JSON

## 🏃‍♂️ Hurtig Start

1.  **Klon og Naviger:**
    ```bash
    git clone <dit-repository-url>
    cd <repository-mappe>
    ```

2.  **Opret og Aktiver Virtuelt Miljø (Anbefalet):**
    ```bash
    python -m venv venv
    # På Windows:
    .\venv\Scripts\activate
    # På Mac/Linux:
    source venv/bin/activate
    ```

3.  **Installer Afhængigheder:**
    Opret en `requirements.txt` fil med følgende indhold og installer:
    ```bash
    # requirements.txt
    streamlit
    pandas
    numpy
    requests
    yfinance
    plotly
    streamlit-aggrid
    ```
    ```bash
    pip install -r requirements.txt
    ```

4.  **Konfigurer API Nøgle (Anbefalet):**
    For at bruge den fulde funktionalitet, især værdiansættelsesmodulet, skal du have en gratis API-nøgle fra [Alpha Vantage](https://www.alphavantage.co/).
    Opret filen `.streamlit/secrets.toml` og tilføj:
    ```toml
    ALPHA_VANTAGE_API_KEY = "DIN_API_NØGLE_HER"
    ```

5.  **Opret Nødvendige Konfigurationsfiler:**
    Opret mappestrukturen og tilføj de nødvendige JSON-filer som beskrevet i dokumentationen (`01_CONFIG_AND_DATA_LOADING.md`):
    ```
    config/
    ├── mappings/
    │   └── region_mappings.json
    └── strategies/
        ├── value_screener_profiles.json
        └── multibagger_profiles.json
    ```

6.  **Tilføj Din Data:**
    Download en "Screener" export fra [Finviz.com](https://finviz.com/screener.ashx) i CSV-format og placér filen i projektroden.

7.  **Kør Applikationen:**
    ```bash
    streamlit run app.py
    ```
    Åbn den URL, der vises i terminalen (typisk http://localhost:8501), for at bruge applikationen.

## 🤝 Bidrag

Bidrag er meget velkomne! Applikationen er bygget modulært, hvilket gør det nemt at forbedre eksisterende moduler eller tilføje nye funktioner.
1.  **Opret en Issue:** Rapporter en fejl eller foreslå en ny funktion via GitHub Issues.
2.  ​**Fork og Pull Request:**​
    *   Fork projektet på GitHub.
    *   Opret en feature gren (`git checkout -b feature/AmazingFeature`).
    *   Commit dine ændringer (`git commit -m 'Add some AmazingFeature'`).
    *   Push til grenen (`git push origin feature/AmazingFeature`).
    *   Åbn en Pull Request mod main/master branchen.

## 📜 Licens

Dette projekt er distribueret under **MIT-licensen**. Se filen [LICENSE.md](LICENSE.md) for yderligere oplysninger.