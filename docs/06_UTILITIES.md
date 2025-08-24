Her er den tekniske dokumentation for de angivne utility-filer, udformet i henhold til den specificerede prompt.

# Projektdokumentation: Utilities & Core Services

## 1. Overordnet Projektdokumentation

### Projektoversigt

*   **Formål:** At levere en samling af robuste, genbrugelige hjælpefunktioner og kerne-services, der understøtter hele applikationen. Disse moduler håndterer tværgående opgaver som datavalidering, UI-komponent-rendering, interaktivitets-forbedringer og persistens af brugerdata.
*   **Anvendelsesområde:** Funktionerne i disse moduler anvendes på tværs af UI-laget (`pages/`) og forretningslogikken (`core/`) for at sikre konsistens, reducere kodeduplikering og forbedre applikationens overordnede robusthed og brugeroplevelse.
*   **Teknologistak:** Python 3.9+, Streamlit, Pandas, st-aggrid.

## 2. Dokumentation pr. Fil

### `utils/validation.py`

*   **Formål:** Centraliserer logik for validering af input-data og sikker rendering af UI-komponenter. Formålet er at fange potentielle datafejl tidligt og forhindre, at applikationen crasher.
*   **Nøglekomponenter:**
    *   **Funktion:** `validate_screening_data(df, profile_config)`
        *   Sammenligner de kolonner, der kræves af en given screeningsprofil, med de kolonner, der findes i den uploadede DataFrame.
        *   Returnerer en liste af kritiske `validation_errors` (hvis kolonner mangler) og en liste af `warnings` (hvis en kolonne har en høj andel af manglende data).
    *   **Funktion:** `safe_aggrid_display(df_for_grid, grid_options, grid_key)`
        *   En wrapper-funktion omkring `AgGrid`-kaldet.
        *   Implementerer en `try...except`-blok, der fanger eventuelle fejl under tabel-rendering og viser en simpel, ikke-interaktiv `st.dataframe` som fallback.
        *   Beregner dynamisk en passende højde for tabellen for at undgå unødvendig scrolling i UI'et.
*   **Afhængigheder:**
    *   **Interne Moduler:** Ingen.
    *   **Eksterne Biblioterker:** `streamlit`, `pandas`, `st_aggrid`.

### `utils/aggrid_helpers.py`

*   **Formål:** Isolerer og centraliserer al JavaScript-kode, der bruges til at forbedre og tilpasse `st-aggrid`-tabellerne. Dette gør UI-koden i `pages/`-filerne renere og mere læsbar.
*   **Nøglekomponenter:**
    *   **Cell Renderers (Interaktivitet):**
        *   `JS_FAVORITE_CELL_RENDERER`: En JavaScript-klasse, der renderer et `<div>` med et "⭐" eller "➕" ikon. Den har en `click`-event listener, som opdaterer cellens værdi og dermed sender en notifikation tilbage til Python-backend'et, når en bruger klikker på ikonet.
        *   `JS_TICKER_LINK_RENDERER`: En simpel renderer, der omdanner en ticker-streng (f.eks. "AAPL") til et HTML `<a>`-tag, der linker direkte til aktiens side på Finviz.
    *   **Value Formatters (Visuel Formatering):**
        *   En samling af JavaScript-funktioner (`JS_MARKET_CAP_FORMATTER`, `JS_PRICE_FORMATTER`, `JS_PERCENTAGE_FORMATTER`, etc.), der modtager en numerisk værdi og returnerer en formateret streng (f.eks. `$1.2B`, `$150.25`, `25.1%`).
    *   **Row Styling:**
        *   `JS_FAVORITE_ROW_STYLE`: En JavaScript-funktion, der betinget anvender en baggrundsfarve på en hel række, hvis `is_favorite`-kolonnen for den række er `true`.
*   **Afhængigheder:**
    *   **Interne Moduler:** Ingen.
    *   **Eksterne Biblioteker:** `st_aggrid` (specifikt `JsCode`-klassen).

### `core/favorites_manager.py` (Dokumentation baseret på beskrivelse)

*   **Formål:** Håndterer simpel, fil-baseret persistens af brugerens favoritliste, så den bevares mellem applikationssessioner.
*   **Nøglekomponenter:**
    *   **Funktion:** `load_favorites()`
        *   Læser `favorites.txt`-filen linje for linje.
        *   Returnerer en liste af ticker-strenge. Hvis filen ikke eksisterer, returneres en tom liste uden fejl.
    *   **Funktion:** `save_favorites(tickers)`
        *   Overskriver `favorites.txt` med den aktuelle liste af favoritter. Hver ticker skrives på en ny linje.
*   **Afhængigheder:**
    *   **Interne Moduler:** Ingen.
    *   **Eksterne Biblioteker:** `os` (standardbibliotek).
*   **Eksempel på Anvendelse:**
    ```python
    from core.favorites_manager import load_favorites, save_favorites

    # Indlæs favoritter ved app-start
    st.session_state.favorites = load_favorites()

    # Gem opdaterede favoritter efter en brugerhandling
    st.session_state.favorites.append('NEWTICKER')
    save_favorites(st.session_state.favorites)
    ```

## 3. Projektstruktur og Relationer

### Mappestruktur

Utility-funktionerne er logisk opdelt i en `utils/`-mappe for generelle UI- og valideringsværktøjer, og en `core/`-mappe for kerne-services som favoritstyring.

```
.
├── utils/
│   ├── __init__.py
│   ├── aggrid_helpers.py   # JavaScript-kode til AgGrid
│   └── validation.py       # Datavalidering og sikker UI-rendering
├── core/
│   ├── __init__.py
│   └── favorites_manager.py  # Gem/indlæs favoritliste
└── pages/
    └── ... (alle UI-sider, der bruger disse utilities)
```

### Arkitektonisk Overblik

Disse moduler fungerer som et fundamentalt service-lag for applikationen. De indeholder ikke selvstændig forretningslogik, men leverer specialiserede, genbrugelige værktøjer, der kaldes af de mere komplekse moduler.

*   **Relation til `pages/`:** Alle filer i `pages/`-mappen, der viser en interaktiv tabel, importerer og anvender funktioner og `JsCode`-objekter fra både `utils/validation.py` og `utils/aggrid_helpers.py`. Dette sikrer en ensartet brugeroplevelse og robusthed på tværs af alle tabeller.
*   **Relation til `core/` og `pages/`:** Både screener-siderne og favorit-siden importerer `load_favorites` og `save_favorites` fra `core/favorites_manager.py` for at læse og skrive til den delte favoritliste. Dette centraliserer ansvaret for datapersistens.
*   **DRY-princippet (Don't Repeat Yourself):** Ved at centralisere logik som f.eks. validering og JavaScript-formatering undgår applikationen kodeduplikering. Hvis formateringen af market cap skal ændres, skal det kun gøres ét sted (`aggrid_helpers.py`), og ændringen vil automatisk gælde for alle tabeller i applikationen.