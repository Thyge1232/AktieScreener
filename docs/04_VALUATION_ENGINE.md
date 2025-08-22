# 4. Værdiansættelses-motor

Modulet `core/valuation/valuation_engine.py` er en selvstændig finansiel modellerings-motor, der er designet til at udføre en fundamental værdiansættelse af en virksomhed. Den er bygget op af flere specialiserede klasser, der hver især håndterer en del af den samlede analyse.

## Arkitektur: Klasse-baseret Design

Motoren er implementeret ved hjælp af et objektorienteret design for at adskille de forskellige beregnings-ansvar.

*   **Dataclasses (`CompanyProfile`, `ValuationInputs`, `WACCInputs`):** Disse fungerer som strukturerede data-containere. De sikrer, at data, der sendes mellem de forskellige beregningsklasser, er veldefinerede og konsistente.
*   **`WACCCalculator`:** En statisk klasse, der udelukkende er ansvarlig for at beregne WACC (Weighted Average Cost of Capital) baseret på CAPM-modellen.
*   **`DCFValuation`:** En statisk klasse, der implementerer en 5-årig Discounted Cash Flow-model.
*   **`ScenarioAnalysis`:** En statisk klasse, der tager et sæt basis-input og genererer tre nye sæt inputs: et for `best-case`, `base-case` og `worst-case`.
*   **`ComprehensiveValuation` (Orchestrator):** Dette er hovedklassen. Den tager en virksomhedsprofil, initialiserer de andre klasser og orkestrerer hele flowet: beregn WACC -> udfør DCF på basis-input -> kør scenarieanalyse -> saml alle resultaterne.

## Implementering af DCF-modellen (`DCFValuation`)

Dette er den centrale værdiansættelsesalgoritme.

1.  **Input Sanity Checks:** Før beregning tjekker funktionen, om `free_cash_flow` er positivt. Hvis ikke, estimerer den en konservativ FCF baseret på EBITDA eller omsætning for at undgå fejl.
2.  **FCF Projektion:**
    -   Den projicerer Free Cash Flow for de næste 5 år.
    -   For at gøre modellen mere realistisk, anvender den en **degressiv vækstrate**. Væksten i år 1 er baseret på `revenue_growth_rate`, men for hvert efterfølgende år dæmpes vækstraten (`adjusted_growth = growth_rate * (0.80 ** (year - 1))`). Dette simulerer, at ekstrem vækst sjældent varer evigt.
3.  **Terminal Værdi:**
    -   Efter de 5 år beregnes en terminal værdi ved hjælp af **Gordon Growth Model**: `TV = (FCF_year5 * (1 + terminal_growth)) / (wacc - terminal_growth)`.
    -   Der er indbygget en vigtig sikkerhedsforanstaltning: den sikrer, at `wacc` altid er højere end `terminal_growth` for at undgå division med nul eller negative værdier.
4.  **Diskontering:**
    -   Hver af de 5 projicerede FCF'er og terminalværdien diskonteres tilbage til deres nutidsværdi ved hjælp af WACC som diskonteringsrente.
    -   Summen af disse diskonterede værdier er virksomhedens samlede `Enterprise Value`.
5.  **Værdi pr. Aktie:** Enterprise Value divideres med `shares_outstanding` for at nå frem til den endelige `value_per_share` (Fair Value).

## Sikkerhedsforanstaltninger og Fejlhåndtering

*   **`safe_numeric`:** En global hjælpefunktion, der sikrer, at alle data, der kommer fra API'en, konverteres sikkert til numeriske værdier. Den håndterer `None`, `NaN` og tomme strenge og returnerer en standardværdi (`0`).
*   **Begrænsning af Ekstremer:** Vækstrater, beta-værdier og gældsforhold bliver "clamped" (begrænset) inden for fornuftige rammer (f.eks. `beta = max(0.5, min(2.0, beta))`) for at forhindre, at ekstreme input-værdier fører til absurde resultater.
*   **Fallback-værdier:** Hvis en kritisk beregning fejler, fanges fejlen, og der returneres fornuftige standardværdier (f.eks. WACC = 10%), så hele værdiansættelsen ikke fejler.