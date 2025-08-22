# 5. UI Implementering

Dette dokument beskriver, hvordan brugergrænsefladen er bygget ved hjælp af Streamlit, og hvordan de interaktive komponenter er implementeret.

## Applikationens Struktur (`app.py`)

`app.py` fungerer som applikationens indgangspunkt og primære router.

*   **State Management:**
    -   Applikationen er stærkt afhængig af `st.session_state` for at opretholde en vedvarende tilstand mellem brugerinteraktioner og "sider".
    -   **Nøglevariabler:**
        -   `processed_dataframe`: Indeholder de rensede CSV-data. Initialiseres én gang ved start.
        -   `favorites`: En liste af ticker-strenge, der synkroniseres på tværs af alle moduler.
        -   `force_rerender_count`: En tæller, der bruges til at tvinge AgGrid-tabellen til at genindlæse fuldstændigt ved at give den en ny, unik `key`. Dette er en kritisk teknik for at sikre, at UI'et afspejler ændringer i favorit-status.

*   **Navigation/Routing:**
    -   Applikationen bruger **ikke** Streamlits indbyggede multipage-app funktionalitet.
    -   I stedet bruges en simpel `if/elif`-struktur baseret på valget i `st.sidebar.selectbox`.
    -   Den valgte sides kode bliver dynamisk eksekveret ved hjælp af `exec(open('pages/filnavn.py').read())`.
    -   **Fordel:** Denne metode sikrer, at alle "sider" deler den samme globale `st.session_state` problemfrit, hvilket er ideelt for denne type tæt integrerede applikation.

## Side-implementeringer (`pages/`)

Hver fil i `pages/`-mappen er ansvarlig for at tegne en specifik side. De følger et fælles mønster:

1.  **Hent Data:** Henter den nødvendige data fra `st.session_state` (f.eks. `df_raw = st.session_state['processed_dataframe']`).
2.  **Sidebar/Input:** Tegner de specifikke input-widgets for siden (f.eks. profil-vælger, regions-filter, avancerede vægt-skydere) i `st.sidebar`.
3.  **Kald Kerne-logik:** Kalder den relevante funktion fra `core/` (f.eks. `screen_stocks_value(...)` eller `get_valuation_data(...)`).
4.  **Vis Resultater:** Formaterer de returnerede data og viser dem i hovedområdet ved hjælp af `st.metric`, `st.dataframe`, `plotly_chart` og især `AgGrid`.

## Interaktiv Tabel (`st-aggrid`)

Den interaktive tabel er en central del af brugeroplevelsen.

*   **`safe_aggrid_display`:** Som beskrevet i `UTILITIES.md`, bruges denne wrapper til at vise tabellen og fange eventuelle fejl, så appen ikke går ned. Den beregner også en dynamisk højde for tabellen for at undgå unødvendig scrolling.
*   **`GridOptionsBuilder`:** Dette er et hjælpeværktøj fra `st-aggrid` til at bygge den komplekse JSON-konfiguration for tabellen på en Pythonisk måde.
*   **JavaScript Integration (`utils/aggrid_helpers.py`):**
    -   For at opnå avanceret interaktivitet (som klikbare favorit-knapper) og custom formatering (som "$1.2B"), bruges `JsCode`-objekter.
    -   **Cell Renderers:** Disse er JavaScript-klasser, der definerer, hvordan en celles HTML skal se ud og opføre sig. `JS_FAVORITE_CELL_RENDERER` opretter et `div`-element med et ikon og en `click`-event listener. Når der klikkes, bruger den AgGrids API (`params.node.setDataValue`) til at sende en opdatering tilbage til Python-backend'et.
    -   **Value Formatters:** Disse er simple JavaScript-funktioner, der modtager en værdi og returnerer en formateret streng.
    -   **Kommunikation (Python <-> JS):** Opdateringer fra JS til Python (f.eks. et klik på favorit-knappen) håndteres ved at fange `grid_response`-objektet. Koden tjekker derefter, om dataen i `grid_response` er forskellig fra den oprindelige data, og hvis den er, gemmes de nye favorit-statusser.