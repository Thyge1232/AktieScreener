# 1. Konfiguration og Dataloading

Dette dokument beskriver den indledende fase af applikationens livscyklus: hvordan den indlæser sine regler (konfiguration) og sine rådata (CSV-fil).

## Konfigurations-Framework (`config_loader.py`)

Al logik for screeningerne er styret af eksterne JSON-filer. Dette er et bevidst designvalg for at adskille logik fra kode, hvilket gør det nemt at tilføje eller justere strategier.

*   **Implementering:** `config_loader.py` indeholder funktioner, der bruger `os.getcwd()` og `os.path.join()` til at bygge pålidelige stier til `config/`-mappen. Hver indlæsningsfunktion (`load_value_config`, etc.) er dekoreret med `@st.cache_data`, hvilket sikrer, at fil-I/O kun sker én gang pr. session, hvilket er ekstremt effektivt.

*   **Struktur af en Screeningsprofil (`.json`):**
    En profil består af `description`, `min_score`, `pre_filters` og `filters`. Et `filter`-objekt er kernen:
    ```json
    "roic_range": {
      "data_key": "Return on Invested Capital",
      "type": "range",
      "description": "...",
      "normalization": "sector_median_relative",
      "ranges": [
        {"min": 1.6, "max": null, "points": 33}
      ]
    }
    ```
    -   `data_key`: Den præcise kolonneoverskrift fra Finviz CSV'en.
    -   `type`: Definerer hvilken evaluerings-algoritme fra `core/screening/utils.py`, der skal anvendes (`range`, `scaled`, `hybrid_range_scaled`).
    -   `description`: Tekst, der vises som tooltip i UI'et.
    -   `normalization`: (Valgfri) Angiver, om der skal anvendes sektor-normalisering. `sector_median_relative` betyder, at højere værdier er bedre, mens `_inverse` betyder, at lavere værdier er bedre.
    -   `ranges`/`min_value`/`max_value`: De specifikke parametre, som evaluerings-algoritmen bruger.

## Rådata-behandling (`core/data/csv_processor.py`)

Dette modul er ansvarligt for at tage den potentielt "beskidte" CSV-fil fra Finviz og omdanne den til en ren, struktureret og fuldt numerisk DataFrame.

*   **Implementering:** Funktionen `process_finviz_csv` er den centrale arbejdshest. Den er også dekoreret med `@st.cache_data` for maksimal ydeevne.
*   **Rensningstrin:**
    1.  **Indlæsning:** Bruger `pd.read_csv` med `on_bad_lines='skip'` og `quoting=1` for at håndtere Finviz' til tider inkonsistente formatering.
    2.  **Kolonne-rensning:** Fjerner overflødige anførelsestegn og mellemrum fra kolonnenavne.
    3.  **Parsing af Strenge:**
        -   `parse_market_cap`: Konverterer strenge som "150B" til det fulde tal `150_000_000_000`.
        -   **Procent-kolonner:** Identificerer dynamisk kolonner, der indeholder procenter, fjerner '%' tegnet, og dividerer med 100 for at få en float-repræsentation (f.eks. `0.25`).
    4.  **Generel Numerisk Konvertering:** Bruger `pd.to_numeric(errors='coerce')` på alle relevante kolonner. Dette er en robust metode, der automatisk erstatter alle ikke-numeriske værdier (som f.eks. '-') med `NaN`, som Pandas' matematiske operationer kan håndtere korrekt.
    5.  **Beregning af Afledte Metrikker:** Beregner nye kolonner som `Price vs. Book/sh` direkte, så de er klar til brug i screeningerne.