Her er den tekniske dokumentation for `core/valuation/` modulerne, udformet i henhold til den specificerede prompt.

# Projektdokumentation: Financial Valuation Engine

## 1. Overordnet Projektdokumentation

### Projektoversigt

*   **Formål:** At levere en avanceret og modulær motor til fundamental værdiansættelse af børsnoterede selskaber. Systemet kombinerer flere anerkendte finansielle modeller for at producere en robust og velbegrundet estimering af en akties indre værdi.
*   **Anvendelsesområde:** Fungerer som den analytiske kerne i et finansielt dashboard. Motoren er designet til at blive kaldt af en UI-komponent (f.eks. Streamlit), der leverer en ticker, hvorefter motoren returnerer en komplet værdiansættelsesrapport.
*   **Teknologistak:** Python 3.9+, NumPy, Pandas, Dataclasses.

## 2. Dokumentation pr. Fil

### `core/valuation/valuation_config.py`

*   **Formål:** Centraliserer alle finansielle antagelser, markedsparametre og modelvægtninger. Dette gør det nemt at justere motorens adfærd uden at ændre i beregningslogikken.
*   **Nøglekomponenter:**
    *   **Klasse:** `ValuationConfig`
        *   En `dataclass`, der indeholder alle konfigurerbare parametre.
        *   **Markedsantagelser:** `risk_free_rate`, `market_premium`.
        *   **DCF-parametre:** `dcf_projection_years_default`, `dcf_fade_factor`.
        *   **Vægtninger:** `valuation_weights` definerer, hvordan de forskellige værdiansættelsesmetoder (DCF, P/E, etc.) vægtes baseret på virksomhedstype.
        *   **Scenarieanalyse:** `sensitivity_wacc_variation`, `sensitivity_growth_variation`.
*   **Afhængigheder:**
    *   **Interne Moduler:** Ingen.
    *   **Eksterne Biblioteker:** `dataclasses`.
*   **Eksempel på Anvendelse:**
    ```python
    from .valuation_config import ValuationConfig

    # Opret en standard konfiguration
    config = ValuationConfig()

    # Juster en parameter
    config.risk_free_rate = 0.035
    ```

### `core/valuation/valuation_inputs.py`

*   **Formål:** Definerer en standardiseret datastruktur for alle de finansielle input, der kræves til en værdiansættelse. Klassen indeholder indbygget validering og normalisering.
*   **Nøglekomponenter:**
    *   **Klasse:** `ValuationInputs`
        *   En `dataclass`, der samler over 20 finansielle nøgletal (omsætning, EBITDA, gæld, etc.).
        *   `__post_init__()`: Metode, der automatisk kaldes efter initialisering for at køre validering.
        *   `_validate_inputs()`: Tjekker for logiske konsistensfejl (f.eks. at EBITDA ikke overstiger omsætning).
        *   `_normalize_growth_rates()`: Sikrer, at vækstrater holdes inden for realistiske grænser (f.eks. -50% til +100%).
*   **Afhængigheder:**
    *   **Interne Moduler:** Ingen.
    *   **Eksterne Biblioteker:** `dataclasses`, `logging`.

### `core/valuation/classifier.py`

*   **Formål:** Klassificerer en virksomhed i en foruddefineret kategori (f.eks. `MATURE`, `GROWTH`, `BANK`) baseret på dens finansielle profil og sektor. Klassifikationen bruges til at vælge de mest relevante værdiansættelsesmetoder.
*   **Nøglekomponenter:**
    *   **Klasse:** `IntelligentCompanyClassifier`
        *   `CLASSIFICATION_RULES`: En dictionary, der definerer de regler (finansielle intervaller og sektor-nøgleord), der kendetegner hver virksomhedstype.
        *   `classify_company(fundamental_data, sector)`: Hovedmetoden, der tager rå finansielle data som input og returnerer den bedst matchende virksomhedstype samt en konfidensscore.
*   **Afhængigheder:**
    *   **Interne Moduler:** `core.valuation.wacc_calculator` (for `CompanyType` Enum), `core.data.validators`.
    *   **Eksterne Biblioteker:** Ingen.

### `core/valuation/wacc_calculator.py`

*   **Formål:** Beregner Weighted Average Cost of Capital (WACC), som er den diskonteringsrente, der anvendes i DCF-modellen. Implementeringen er avanceret og justerer for virksomhedsspecifikke risici.
*   **Nøglekomponenter:**
    *   **Klasser:** `WACCInputs`, `CompanyProfile` (dataclasses til input).
    *   **Klasse:** `WACCCalculator`
        *   `calculate_comprehensive_wacc(...)`: Hovedmetoden, der orkestrerer WACC-beregningen.
        *   `_calculate_risk_adjustments(...)`: Beregner risikotillæg baseret på virksomhedens størrelse, gældsniveau og forretningsmodel (f.eks. `STARTUP` vs. `UTILITY`).
*   **Afhængigheder:**
    *   **Interne Moduler:** `core.data.client` (for `safe_numeric`).
    *   **Eksterne Biblioteker:** `logging`, `dataclasses`.

### `core/valuation/risk_assessment.py`

*   **Formål:** Udfører en omfattende risikovurdering af virksomheden på tværs af fire dimensioner: finansiel, forretningsmæssig, markedsrelateret og likviditetsmæssig risiko.
*   **Nøglekomponenter:**
    *   **Klasse:** `RiskAssessment`
        *   `assess_company_risk(inputs, profile)`: Hovedmetoden, der returnerer en samlet risikoscore (0-100), et risikoniveau (`LOW`, `MEDIUM`, `HIGH`), samt en liste over de primære identificerede risikofaktorer.
        *   `_assess_financial_risk(...)`, `_assess_business_risk(...)` etc.: Private metoder, der hver især scorer en specifik risikokategori.
*   **Afhængigheder:**
    *   **Interne Moduler:** `core.valuation.dcf_engine` (for `ValuationInputs`).
    *   **Eksterne Biblioteker:** `logging`, `dataclasses`.

### `core/valuation/comparable_valuation.py`

*   **Formål:** Implementerer værdiansættelse baseret på sammenlignelige multipla (P/E, EV/EBITDA, P/B). Metoderne justerer industristandarder baseret på virksomhedens vækst og rentabilitet.
*   **Nøglekomponenter:**
    *   **Klasse:** `ComparableValuation`
        *   `calculate_pe_valuation(...)`: Beregner en fair værdi baseret på P/E-multipel, justeret for vækst (PEG-tilgang).
        *   `calculate_ev_ebitda_valuation(...)`: Beregner fair værdi baseret på EV/EBITDA.
        *   `calculate_price_to_book(...)`: Beregner fair værdi baseret på P/B, justeret for egenkapitalforrentning (ROE).
*   **Afhængigheder:**
    *   **Interne Moduler:** `core.valuation.dcf_engine` (for `ValuationInputs`).
    *   **Eksterne Biblioteker:** `logging`.

### `core/valuation/dcf_engine.py`

*   **Formål:** Indeholder den centrale Discounted Cash Flow (DCF) model. Modulet er designet til at være robust med input-validering, en flertrins vækstmodel og integration med scenarieanalyse.
*   **Nøglekomponenter:**
    *   **Klasse:** `DCFEngine`
        *   `calculate_core_dcf(...)`: En "ren" DCF-beregning uden scenarieanalyse. Denne metode er sikker at kalde fra andre moduler (f.eks. `ScenarioAnalysis`) for at undgå cirkulære afhængigheder.
        *   `calculate_comprehensive_dcf(...)`: Hovedmetoden, der først kalder `calculate_core_dcf` og derefter tilføjer resultater fra sensitivitets- og Monte Carlo-analyser.
        *   `_create_growth_stages(...)`: Implementerer en model, hvor væksten gradvist aftager over en årrække.
*   **Afhængigheder:**
    *   **Interne Moduler:** `valuation_inputs`, `valuation_config`, `scenario_analysis` (lokal import).
    *   **Eksterne Biblioteker:** `logging`, `threading`.

### `core/valuation/scenario_analysis.py`

*   **Formål:** Udfører avanceret usikkerhedsanalyse på DCF-resultatet. Dette giver et mere nuanceret billede af værdiansættelsen end et enkelt punktestimat.
*   **Nøglekomponenter:**
    *   **Klasse:** `ScenarioAnalysis`
        *   `perform_sensitivity_analysis(...)`: Beregner, hvordan den estimerede fair værdi ændrer sig, når nøgleinput som WACC og vækstrate varieres.
        *   `monte_carlo_simulation(...)`: Kører tusindvis af DCF-beregninger med små, tilfældige variationer i input for at generere et sandsynlighedsinterval (konfidensinterval) for fair værdi.
*   **Afhængigheder:**
    *   **Interne Moduler:** `valuation_inputs`, `valuation_config`, `dcf_engine` (lokal import).
    *   **Eksterne Biblioteker:** `numpy`, `logging`.

### `core/valuation/valuation_engine.py`

*   **Formål:** Fungerer som den øverste orkestrator for hele værdiansættelsesprocessen. Dette er det primære adgangspunkt for eksterne kald.
*   **Nøglekomponenter:**
    *   **Klasse:** `ComprehensiveValuationEngine`
        *   `perform_comprehensive_valuation(ticker, ...)`: Hovedmetoden, der styrer hele flowet: datahentning, klassifikation, WACC-beregning, kørsel af alle værdiansættelsesmodeller, risikovurdering og til sidst en vægtet sammenfatning af resultaterne.
        *   `_create_valuation_inputs(...)`: Mapper rå data fra API-kald til den strukturerede `ValuationInputs` klasse.
        *   `_calculate_weighted_fair_value(...)`: Kombinerer resultaterne fra DCF, P/E, EV/EBITDA og P/B baseret på de vægtninger, der er defineret i `ValuationConfig`.
*   **Afhængigheder:**
    *   **Interne Moduler:** Alle andre moduler i `core/valuation/` samt `core.data.client`.
    *   **Eksterne Biblioteker:** `pandas`, `numpy`, `logging`.

## 3. Projektstruktur og Relationer

### Mappestruktur

Værdiansættelsesmotoren er logisk adskilt i sit eget underbibliotek, `core/valuation/`, hvilket fremmer genbrug og testbarhed.

```
core/
└── valuation/
    ├── __init__.py
    ├── valuation_engine.py      # Orkestrator (Entry Point)
    ├── dcf_engine.py            # Kerne DCF-model
    ├── wacc_calculator.py       # Beregning af diskonteringsfaktor
    ├── comparable_valuation.py  # Multipla-baserede metoder
    ├── risk_assessment.py       # Kvalitativ og kvantitativ risikovurdering
    ├── scenario_analysis.py     # Usikkerhedsanalyse (Monte Carlo, Sensitivitet)
    ├── classifier.py            # Klassifikation af virksomhedstype
    ├── valuation_config.py      # Central konfiguration og antagelser
    └── valuation_inputs.py      # Standardiseret input-datastruktur
```

### Arkitektonisk Overblik

Systemet er bygget op omkring `ComprehensiveValuationEngine` som den centrale koordinator. Flowet for en fuld værdiansættelse er som følger:

1.  **Input:** Et eksternt kald (f.eks. fra en UI) kalder `perform_comprehensive_valuation` i `valuation_engine.py` med et aktiesymbol.
2.  **Datahentning:** Motoren bruger `core.data.client` til at hente de nødvendige finansielle data.
3.  **Klassifikation:** `classifier.py` analyserer dataene og bestemmer virksomhedstypen (f.eks. "growth").
4.  **Input Standardisering:** Rå data konverteres til en valideret `ValuationInputs` instans.
5.  **Parallel Beregning:**
    *   `wacc_calculator.py` beregner den virksomhedsspecifikke WACC.
    *   `dcf_engine.py` bruger WACC til at beregne en fair værdi baseret på fremtidige pengestrømme. Denne proces inkluderer kald til `scenario_analysis.py`.
    *   `comparable_valuation.py` beregner fair værdier baseret på P/E, EV/EBITDA og P/B.
    *   `risk_assessment.py` genererer en risikoprofil.
6.  **Syntese:** `valuation_engine.py` indsamler alle resultater. Ved hjælp af `valuation_config.py` henter den de korrekte vægtninger for den klassificerede virksomhedstype.
7.  **Output:** En vægtet gennemsnitlig fair værdi beregnes og returneres sammen med alle delresultater (DCF, WACC, risikoanalyse etc.) i en samlet dictionary.