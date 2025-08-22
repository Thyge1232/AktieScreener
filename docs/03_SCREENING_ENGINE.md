# 3. Screenings-motor

Kernen af screeningslogikken findes i `core/screening/`. Dette er den motor, der transformerer en stor mængde aktiedata til en prioriteret liste baseret på en given investeringsstrategi.

## Arkitektur

Screenings-motoren består af tre hoveddele, der arbejder sammen:

1.  **Orchestrator-scripts (`value_screener.py`, `multibagger_screener.py`):** Disse er højniveau-funktionerne, der definerer den overordnede screenings-pipeline.
2.  **Evaluerings-værktøjer (`utils.py`):** En samling af lavniveau, "rene" funktioner, der hver især udfører én specifik type pointberegning.
3.  **Normaliserings-modul (`utils.py` -> `SectorNormalizer`):** En specialiseret klasse, der håndterer den komplekse opgave at justere data for sektor-bias.

## Implementerings-pipeline (`screen_stocks_*` funktionerne)

Hver `screen_stocks_*` funktion følger en identisk, veldefineret pipeline:

1.  **Indlæsning & Filtrering:**
    -   Indlæser konfigurationsfiler og region-mappings.
    -   Udfører et indledende, groft filter på dataen baseret på `region` og `pre_filters` (f.eks. fjern alle aktier med Market Cap < 300M). Dette reducerer datamængden, som de tungere beregninger skal arbejde på.

2.  **Initialisering:**
    -   `SectorNormalizer`-klassen initialiseres med den for-filtrerede DataFrame. I sin `__init__`-metode forudberegner den med det samme alle nødvendige sektor-statistikker (medianer) og cacher dem.
    -   Nye kolonner (`points_*` og `Score`) tilføjes til DataFrame'en og initialiseres til `0.0`.

3.  **Scoring Loop:**
    -   Dette er kernen. Funktionen itererer over hvert `filter`-objekt defineret i JSON-profilen.
    -   **Normaliseringstrin:** `apply_normalization()` kaldes. Hvis `filter.normalization` er sat, kalder den `normalizer.normalize_by_percentile()`. Denne metode bruger `pandas.groupby('Sector').rank(pct=True)` til at beregne en percentil-rang for hver aktie *inden for sin sektor*. Resultatet er en ny Pandas Series, hvor de absolutte værdier er erstattet af en relativ, sektor-justeret score.
    -   **Point-beregning:** Den (potentielt normaliserede) Series sendes til den relevante evalueringsfunktion (`evaluate_range_filter`, `evaluate_scaled_filter` etc.) baseret på `filter.type`. Denne funktion returnerer en "rå" pointscore.
    -   **Vægtning:** Den rå score ganges med den dynamiske vægt fra UI'et (`dynamic_weights`) og gemmes i den tilsvarende `points_*` kolonne.
    -   **Akkumulering:** De vægtede point lægges til den samlede `Score`-kolonne.

4.  **Finalisering:**
    -   En `Score_Percent` beregnes ved at dividere den samlede `Score` med den maksimalt mulige score.
    -   Resultaterne filtreres igen baseret på `min_score` fra profilen.
    -   DataFrame'en sorteres efter `Score_Percent` i faldende rækkefølge.
    -   Et udvalg af relevante kolonner returneres til UI-laget.

## Nøglealgoritme: `SectorNormalizer`

Dette er den mest sofistikerede del af screenings-motoren.

*   **Problem:** Et P/E-forhold på 10 er meget lavt (godt) for en teknologivirksomhed, men højt (dårligt) for en forsyningsvirksomhed. En direkte sammenligning er meningsløs.
*   **Løsning:** `normalize_by_percentile` løser dette ved at omdanne absolutte værdier til relative rangeringer.
    -   `is_inverse_metric`: En boolean-parameter styrer, om en høj rangering er god eller dårlig. For P/E (hvor lavere er bedre), sættes den til `True`, hvilket inverterer rangeringen. For ROIC (hvor højere er bedre), er den `False`.
    -   **Output:** Metoden returnerer en score (f.eks. mellem 0 og 2), der repræsenterer, hvor "god" en akties nøgletal er i forhold til dens direkte konkurrenter i samme sektor. Dette giver en ægte "æbler-til-æbler" sammenligning på tværs af hele markedet.