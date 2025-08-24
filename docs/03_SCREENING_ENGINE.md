Her er den tekniske dokumentation for `core/screening/` modulerne, udformet i henhold til den specificerede prompt.

# Projektdokumentation: Stock Screening Engine

## 1. Overordnet Projektdokumentation

### Projektoversigt

*   **Formål:** At levere en fleksibel og kraftfuld screeningsmotor, der kan analysere store datasæt af aktier og rangordne dem baseret på specifikke investeringsstrategier (f.eks. "Value" eller "Multibagger"). Motoren er designet til at håndtere kompleksiteten ved at sammenligne selskaber på tværs af forskellige sektorer.
*   **Anvendelsesområde:** Anvendes som den analytiske kerne i en aktiescreener-applikation. Den modtager en rå DataFrame med aktiedata og en konfigurationsprofil, og returnerer en sorteret og scoret liste af de mest lovende aktier.
*   **Teknologistak:** Python 3.9+, Pandas, NumPy, Streamlit (for caching).

## 2. Dokumentation pr. Fil

### `core/screening/utils.py`

*   **Formål:** Indeholder de fundamentale byggeblokke for screeningsmotoren. Filen er opdelt i to ansvarsområder: (1) en samling af "rene" evalueringsfunktioner, der tildeler point baseret på forskellige regler, og (2) en specialiseret klasse til sektor-normalisering.
*   **Nøglekomponenter:**
    *   **Evalueringsfunktioner:**
        *   `evaluate_condition(...)`: Udfører simple binære tjek (f.eks. `>`, `<`, `between`) og bruges primært til for-filtrering.
        *   `evaluate_range_filter(...)`: Tildeler et fast antal point, hvis en værdi falder inden for et bestemt interval.
        *   `evaluate_scaled_filter(...)`: Tildeler point på en lineær skala mellem en min- og en max-værdi.
        *   `evaluate_percentile_range_filter(...)`: Tildeler point baseret på, hvilken percentil-gruppe en værdi tilhører inden for hele datasættet.
        *   `evaluate_hybrid_range_scaled_filter(...)`: En avanceret kombination, der giver basispoint for at være i et interval og derefter skalerer yderligere point inden for intervallet.
    *   **Klasse: `SectorNormalizer`**
        *   **Formål:** Løser det klassiske problem med at sammenligne nøgletal på tværs af sektorer (f.eks. er et P/E-tal på 15 højt for en bank, men lavt for en tech-virksomhed).
        *   `__init__(df)`: Forudberegner og cacher sektor-medianer for alle numeriske kolonner ved initialisering for at optimere ydeevnen.
        *   `normalize_by_percentile(...)`: Hovedmetoden. Bruger `pandas.groupby('Sector').rank(pct=True)` til at konvertere en absolut værdi (f.eks. P/E = 25) til en relativ rangering inden for dens egen sektor. Returnerer en normaliseret score (typisk mellem 0 og 2), der muliggør en fair "æbler-til-æbler" sammenligning.
*   **Afhængigheder:**
    *   **Interne Moduler:** Ingen.
    *   **Eksterne Biblioteker:** `pandas`, `numpy`.

### `core/screening/value_screener.py`

*   **Formål:** Fungerer som en højniveau-orkestrator for en "Value Investing" screeningsstrategi. Den implementerer en specifik pipeline for databehandling og scoring baseret på en konfigurationsprofil.
*   **Nøglekomponenter:**
    *   **Funktion:** `screen_stocks_value(df, profile_name, ...)`
        *   **Pipeline:** Følger en standardiseret proces:
            1.  **Filtrering:** Anvender først et groft filter baseret på region og `pre_filters` fra konfigurationsprofilen (f.eks. fjern selskaber med Market Cap < 500M).
            2.  **Initialisering:** Opretter en instans af `SectorNormalizer`.
            3.  **Scoring Loop:** Itererer gennem hvert scoringskriterie (`filter`) i profilen. For hvert kriterie kaldes `apply_normalization` (som internt bruger `SectorNormalizer`), hvorefter den normaliserede værdi sendes til den relevante `evaluate_*` funktion fra `utils.py`.
            4.  **Vægtning & Akkumulering:** Den returnerede score vægtes baseret på brugerinput (`dynamic_weights`) og lægges til en samlet `Score`.
            5.  **Finalisering:** Beregner en procentvis score, sorterer resultaterne og returnerer en renset DataFrame til UI'et.
*   **Afhængigheder:**
    *   **Interne Moduler:** `config_loader`, `core.screening.utils`.
    *   **Eksterne Biblioteker:** `pandas`, `streamlit`.
*   **Eksempel på Anvendelse:**
    ```python
    # Anvendes typisk af UI-laget
    from .value_screener import screen_stocks_value

    # Antag at `all_stocks_df` er en DataFrame med alle aktiedata
    # og `config` er indlæst fra en JSON-fil.
    results_df = screen_stocks_value(
        df=all_stocks_df,
        profile_name='deep_value_strategy',
        config=config,
        selected_regions=['Nordics'],
        dynamic_weights={'pe_ratio': 1.5, 'roic': 1.0}
    )
    ```

### `core/screening/multibagger_screener.py`

*   **Formål:** Fungerer som en højniveau-orkestrator for en "Multibagger" (høj vækst) screeningsstrategi. Strukturen og pipelinen er identisk med `value_screener.py`, men den kaldes med en anden konfigurationsprofil, der fokuserer på vækst-metrikker.
*   **Nøglekomponenter:**
    *   **Funktion:** `screen_stocks_multibagger(df, profile_name, ...)`
        *   Implementerer den samme robuste pipeline som `value_screener`: For-filtrering, initialisering af `SectorNormalizer`, en scoring loop der anvender normalisering og evaluering, og til sidst en finalisering af resultaterne. Ved at genbruge den samme pipeline-struktur sikres konsistens og vedligeholdbarhed, mens fleksibiliteten bevares gennem forskellige konfigurationsprofiler.
*   **Afhængigheder:**
    *   **Interne Moduler:** `config_loader`, `core.screening.utils`.
    *   **Eksterne Biblioteker:** `pandas`.

## 3. Projektstruktur og Relationer

### Mappestruktur

Screeningsmotoren er samlet i sit eget `screening` underbibliotek, hvilket skaber en klar adskillelse mellem dataindsamling, screening og værdiansættelse.

```
core/
└── screening/
    ├── __init__.py
    ├── value_screener.py         # Orkestrator for Value-strategi
    ├── multibagger_screener.py   # Orkestrator for Multibagger-strategi
    └── utils.py                  # Kerne-algoritmer (Evaluering & Normalisering)
```

### Arkitektonisk Overblik

Systemet er designet med en klar adskillelse mellem "hvad" der skal gøres (defineret i JSON-konfigurationsprofiler) og "hvordan" det skal gøres (implementeret i Python-koden).

Dataflowet for en screening er som følger:

1.  **UI Kald:** Brugeren vælger en strategi (f.eks. "Value") og justerer vægtningen af forskellige faktorer. Dette resulterer i et kald til den relevante orkestrator-funktion, f.eks. `screen_stocks_value`.
2.  **Orkestrator:** `value_screener.py` modtager den fulde DataFrame. Den udfører indledende filtrering for at reducere datasættet.
3.  **Normalisering:** Under scoring-loopet kalder orkestratoren `apply_normalization` for hvert nøgletal. Denne funktion fungerer som et bindeled til `SectorNormalizer` i `utils.py`.
4.  **Kerne-logik:** `SectorNormalizer` slår den relevante sektor op og beregner en sektor-justeret, relativ score for hver aktie.
5.  **Point-tildeling:** Den normaliserede score returneres til orkestratoren, som sender den videre til den korrekte `evaluate_*` funktion i `utils.py` for at få en "rå" point-værdi.
6.  **Vægtning:** Orkestratoren ganger de rå point med brugerens dynamiske vægtning og lægger resultatet til aktiens samlede score.
7.  **Output:** Efter at have gennemgået alle kriterier, sorteres den endelige DataFrame efter den samlede score og returneres til UI'et for visning.

Denne arkitektur gør systemet ekstremt fleksibelt. En helt ny screeningsstrategi kan oprettes ved blot at tilføje en ny JSON-konfigurationsprofil, uden at der kræves ændringer i Python-koden, så længe de nødvendige evalueringsregler allerede eksisterer i `utils.py`.