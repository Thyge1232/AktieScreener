# Projektdokumentation: Konfigurationslag

## 1. Overordnet Projektdokumentation

### Projektoversigt

*   **Formål:** At levere et robust og centraliseret system til indlæsning af applikationens konfiguration. Dette lag adskiller strategisk logik (defineret i JSON-filer) fra eksekveringskoden, hvilket gør det nemt at tilføje, fjerne eller justere investeringsstrategier uden at ændre i Python-koden.
*   **Anvendelsesområde:** Anvendes ved opstart af applikationen og af screenings-modulerne til at hente de nødvendige profiler og mappings.
*   **Teknologistak:** Python 3.9+, Streamlit (for caching), JSON.

## 2. Dokumentation pr. Fil

### `config_loader.py`

*   **Formål:** Fungerer som den centrale "loader" for alle JSON-baserede konfigurationsfiler. Den håndterer filstier, indlæsning og caching af konfigurationsdata for at sikre optimal ydeevne.
*   **Nøglekomponenter:**
    *   **Funktion:** `load_config(file_path)`
        *   En generisk, cachet funktion (`@st.cache_data`), der kan indlæse enhver JSON-fil fra `config/`-mappen.
        *   Implementerer robust fejlhåndtering, der viser en klar fejlmeddelelse i UI'et, hvis en fil ikke kan findes eller parses.
    *   **Specialiserede funktioner:**
        *   `load_value_config()`: En bekvemmelighedsfunktion, der kalder `load_config` med den specifikke sti til value-profilerne.
        *   `load_multibagger_config()`: Tilsvarende funktion for multibagger-profilerne.
        *   `load_region_mappings()`: Tilsvarende funktion for region-mappings.
*   **Afhængigheder:**
    *   **Interne Moduler:** Ingen.
    *   **Eksterne Biblioteker:** `json`, `os`, `streamlit`.
*   **Eksempel på Anvendelse:**
    ```python
    # I pages/value_screener.py
    from config_loader import load_value_config

    # Indlæs alle value-profiler (resultatet caches automatisk)
    config_vs = load_value_config()
    selected_profile = config_vs.get("Kvalitet (Quality Value)")
    ```

### `config/mappings/region_mappings.json`

*   **Formål:** Definerer en simpel mapping mellem et overordnet regionsnavn (f.eks. "EU & UK") og en liste af specifikke lande, som Finviz bruger i sin `Country`-kolonne.
*   **Struktur:**
    *   En flad JSON-objekt, hvor hver nøgle er et regionsnavn, og værdien er en liste af strenge (lande).
*   **Anvendelse:** Bruges af screener-siderne til at filtrere den primære DataFrame baseret på brugerens valg af regioner i sidebaren.

### `config/strategies/value_screener_profiles.json` og `config/strategies/multibagger_profiles.json`

*   **Formål:** Disse filer er hjertet i screeningsmotorens logik. De definerer de specifikke regler, vægte og beskrivelser for hver enkelt investeringsstrategi.
*   **Struktur (for hver profil):**
    *   **`description`**: En brugervenlig tekst, der forklarer strategiens filosofi.
    *   **`min_score`**: En tærskelværdi for, hvor høj en score en aktie skal have for at blive vist i resultaterne.
    *   **`pre_filters`**: En liste af simple, binære filtre (f.eks. `Market Cap > 1B`), der anvendes *før* den tunge scoring for at forbedre ydeevnen.
    *   **`filters`**: En dictionary, der indeholder de detaljerede scoringsregler. Hver regel specificerer:
        *   **`data_key`**: Navnet på kolonnen i DataFrame'en, der skal evalueres.
        *   **`type`**: Typen af evaluering (`range`, `scaled`, `hybrid_range_scaled`), som mapper direkte til en `evaluate_*` funktion i `utils.py`.
        *   **`description`**: En tooltip-tekst til UI'et.
        *   **`normalization`**: (Valgfri) Angiver, om værdien skal sektor-normaliseres (`sector_median_relative` eller `sector_median_relative_inverse`).
        *   **Specifikke parametre**: Nøgler som `ranges`, `min_value`, `max_value`, etc., der er nødvendige for den valgte `type`.
*   **Anvendelse:** Indlæses af de respektive screener-sider og bruges til at styre hele screenings- og scoringsprocessen dynamisk.

## 3. Projektstruktur og Relationer

### Mappestruktur

Konfigurationsfilerne er organiseret i en dedikeret `config/`-mappe med undermapper for at skabe en logisk struktur.

```
.
├── config_loader.py          # Den centrale loader
└── config/
    ├── mappings/
    │   └── region_mappings.json
    └── strategies/
        ├── multibagger_profiles.json
        └── value_screener_profiles.json
```

### Arkitektonisk Overblik

Dette lag er designet til at være fuldstændig afkoblet fra resten af applikationen. `config_loader.py` fungerer som den eneste bro mellem de statiske JSON-filer og den dynamiske Python-kode.

1.  **UI-kald:** En side som `pages/value_screener.py` kalder `load_value_config()`.
2.  **Loader:** `config_loader.py` tjekker først Streamlits cache. Hvis data ikke er cachet, læser den den relevante JSON-fil fra `config/strategies/`-mappen.
3.  **Retur:** Den parsede dictionary returneres til UI-laget.
4.  **Anvendelse:** UI-laget bruger dictionary'en til at bygge sidebar-kontroller (sliders, tooltips) og sender den derefter videre til kerne-screeningsfunktionen (f.eks. `screen_stocks_value`), som bruger den til at udføre selve screeningen.

Denne arkitektur gør det muligt for en ikke-teknisk bruger at redigere eller tilføje nye screeningsstrategier ved blot at ændre i JSON-filerne, uden behov for at røre Python-koden.
