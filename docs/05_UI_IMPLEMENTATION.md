Her er den tekniske dokumentation for UI-laget (`app.py` og `pages/`), udformet i henhold til den specificerede prompt.

# Projektdokumentation: Streamlit User Interface

## 1. Overordnet Projektdokumentation

### Projektoversigt

*   **Formål:** At levere en interaktiv, web-baseret brugergrænseflade (UI) for en finansiel analyse- og screeningsapplikation. UI'et muliggør data-upload, konfiguration af screeningsstrategier, visning af resultater og administration af en personlig favoritliste.
*   **Anvendelsesområde:** Dette er frontenden for hele applikationen, bygget udelukkende med Streamlit-frameworket. Det fungerer som det primære interaktionspunkt for brugeren.
*   **Teknologistak:** Python 3.9+, Streamlit, Pandas, Plotly, st-aggrid.

## 2. Dokumentation pr. Fil

### `app.py`

*   **Formål:** Fungerer som applikationens centrale indgangspunkt (entrypoint) og router. Den håndterer den overordnede sidestruktur, navigation og initialisering af den globale `session_state`.
*   **Nøglekomponenter:**
    *   **Session State Initialisering:**
        *   Ved første kørsel initialiseres `st.session_state` med nøglevariabler som `processed_dataframe`, `favorites`, og `loaded_csv_filename`.
        *   Forsøger automatisk at indlæse en enkelt `.csv`-fil fra rodmappen for at strømline opstartsprocessen.
    *   **Navigation (Routing):**
        *   Bruger et `st.sidebar.selectbox` til at styre, hvilken "side" der vises.
        *   Implementerer en simpel routing-mekanisme ved hjælp af en `if/elif`-struktur, der dynamisk eksekverer koden fra den relevante fil i `pages/`-mappen via `exec(open(...).read())`. Denne metode sikrer, at alle sider deler den samme `session_state`, hvilket er afgørende for applikationens funktionalitet.
    *   **Global Sidebar:** Konstruerer den primære navigationsmenu og viser global statusinformation (antal indlæste aktier, antal favoritter).
*   **Afhængigheder:**
    *   **Interne Moduler:** `core.data.csv_processor`, `core.favorites_manager`.
    *   **Eksterne Biblioteker:** `streamlit`, `os`, `glob`.

### `pages/value_screener.py` og `pages/multibagger_screener.py`

*   **Formål:** Disse filer implementerer UI'et for de to primære screeningssider. Deres struktur er næsten identisk, hvilket sikrer en konsistent brugeroplevelse og gør koden lettere at vedligeholde.
*   **Nøglekomponenter:**
    *   **Sidebar Controls:** Bygger sidebar-menuen med specifikke indstillinger for den valgte screener, herunder valg af profil, regioner og (i avanceret tilstand) justerbare vægt-sliders for hver screeningsparameter.
    *   **Undo/Redo Funktionalitet:** Implementerer en simpel historik for vægtjusteringer i `st.session_state`, så brugeren kan fortryde og gendanne ændringer.
    *   **Screening Kald:** Kalder den relevante kernefunktion (f.eks. `screen_stocks_value`) med data fra `session_state` og de aktuelle indstillinger fra sidebaren.
    *   **Resultatvisning (AgGrid):**
        *   Bruger `st-aggrid` til at vise de filtrerede og sorterede resultater i en interaktiv tabel.
        *   Anvender `GridOptionsBuilder` til programmatisk at konfigurere tabellen.
        *   Integrerer specialiserede JavaScript-funktioner (`JsCode`) fra `utils/aggrid_helpers.py` til at rendere klikbare favorit-ikoner, links til tickers og tilpasset formatering af tal.
    *   **Favorit-håndtering:** Logikken til at opdatere favoritlisten er implementeret direkte på siden. Den sammenligner tilstanden af `is_favorite`-kolonnen før og efter brugerinteraktion i AgGrid for at bestemme, hvilke tickers der skal tilføjes eller fjernes.
*   **Afhængigheder:**
    *   **Interne Moduler:** `core.screening.*`, `config_loader`, `core.favorites_manager`, `utils.aggrid_helpers`, `utils.validation`.
    *   **Eksterne Biblioteker:** `streamlit`, `pandas`, `st_aggrid`.

### `pages/favorites.py`

*   **Formål:** Viser brugerens gemte favoritaktier og giver mulighed for at hente opdaterede live-data og køre en detaljeret værdiansættelse.
*   **Nøglekomponenter:**
    *   **Datahentning:** Indeholder knapper, der udløser kald til `get_data_for_favorites` (for live-priser) og `get_valuation_data` (for dybdegående analyse) fra `core`-modulerne.
    *   **Resultatvisning (AgGrid):** Viser de hentede data i en AgGrid-tabel. Ligesom screener-siderne bruger den `JsCode` til at rendere et klikbart ikon, der lader brugeren fjerne en aktie fra favoritter direkte i tabellen.
    *   **Session State Håndtering:** Bruger `st.session_state.force_favorites_update` til at signalere til andre sider, at favoritlisten er blevet ændret, hvilket kan udløse en `rerun` for at sikre, at alle UI-komponenter er synkroniserede.
    *   **Sidebar Statistik:** Viser en opsummering af favorit-porteføljen i sidebaren, herunder antal aktier og gennemsnitlige nøgletal.
*   **Afhængigheder:**
    *   **Interne Moduler:** `core.favorites_manager`, `core.data.client`, `core.valuation.valuation_engine`, `utils.validation`, `utils.aggrid_helpers`.
    *   **Eksterne Biblioteker:** `streamlit`, `pandas`, `st_aggrid`.

### `pages/valuation.py`

*   **Formål:** Præsenterer resultaterne af en dybdegående værdiansættelse for en eller flere udvalgte favoritaktier.
*   **Nøglekomponenter:**
    *   **Ticker Valg:** Bruger `st.multiselect` til at lade brugeren vælge, hvilke af deres favoritaktier der skal analyseres.
    *   **Orkestrering af Værdiansættelse:** Kalder `ComprehensiveValuationEngine.perform_comprehensive_valuation` og viser en progress bar, mens de potentielt tidskrævende beregninger og API-kald udføres.
    *   **Struktureret Visning:** Organiserer de komplekse resultater i en overskuelig struktur ved hjælp af `st.tabs` for hver aktie. Hver fane indeholder metrikker, grafer (via `plotly`) og opsummeringer for de forskellige analysemoduler (DCF, WACC, risiko, etc.).
    *   **Fejlhåndtering:** Viser tydelige fejlmeddelelser, hvis en værdiansættelse for en specifik aktie fejler, uden at det afbryder visningen af de succesfulde resultater.
*   **Afhængigheder:**
    *   **Interne Moduler:** `core.valuation.valuation_engine`, `core.favorites_manager`, `utils.validation`, `utils.aggrid_helpers`.
    *   **Eksterne Biblioteker:** `streamlit`, `pandas`, `plotly`.

## 3. Projektstruktur og Relationer

### Mappestruktur

UI-koden er organiseret i en `pages/`-mappe, som er en almindelig konvention i Streamlit-projekter, selvom den indbyggede multipage-funktionalitet ikke anvendes direkte. Hovedfilen `app.py` ligger i rodmappen.

```
.
├── app.py                      # Hoved-applikation og router
├── pages/
│   ├── favorites.py            # UI for favoritliste
│   ├── multibagger_screener.py # UI for Multibagger-screener
│   ├── valuation.py            # UI for værdiansættelsesside
│   └── value_screener.py       # UI for Value-screener
├── core/
│   ├── data/
│   ├── screening/
│   └── valuation/
└── utils/
    ├── aggrid_helpers.py
    └── validation.py
```

### Arkitektonisk Overblik

Applikationen følger en klar arkitektur, hvor UI-laget (`app.py` og `pages/`) er adskilt fra forretningslogikken (`core/`).

1.  **Opstart:** `app.py` starter, initialiserer `session_state` og indlæser data.
2.  **Navigation:** Brugeren vælger en side i sidebaren. `app.py` fungerer som en router og eksekverer den relevante fil fra `pages/`-mappen.
3.  **Interaktion:** En sidefil (f.eks. `value_screener.py`) bygger sit UI. Brugeren interagerer med widgets (sliders, knapper etc.).
4.  **Kald til Core:** Brugerinteraktioner udløser kald til funktioner i `core/`-mapperne. For eksempel kalder `value_screener.py` `screen_stocks_value()` fra `core/screening/`.
5.  **Dataretur:** `core`-funktionerne returnerer resultater (typisk som en Pandas DataFrame eller en dictionary) til den kaldende side-fil.
6.  **Rendering:** Side-filen formaterer de modtagne data og viser dem ved hjælp af Streamlit-komponenter, primært `st-aggrid`.
7.  **State Opdatering:** Hvis brugeren foretager en handling, der ændrer den delte tilstand (f.eks. tilføjer en favorit), opdateres `st.session_state.favorites`. Dette sikrer, at ændringen er tilgængelig for alle andre sider ved næste `rerun`.