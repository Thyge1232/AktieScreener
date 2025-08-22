# 👩‍💻 Udviklerguide til Investment Screener

Velkommen, udvikler! Dette dokument giver et overblik over projektets arkitektur, de centrale designprincipper og fungerer som din primære indgang til den dybdegående tekniske dokumentation.

## 1. Projektstruktur

Projektet er bygget op omkring en klar og modulær struktur, der adskiller UI, forretningslogik og datahåndtering.

```
.
├── .streamlit/
│   └── secrets.toml        # API nøgler og andre hemmeligheder
├── config/                 # Alle screenings-strategier og mappings
├── core/                   # Applikationens kerne-logik (hjernen)
├── docs/                   # Fuld teknisk dokumentation
├── pages/                  # UI-kode for hver Streamlit-side
├── utils/                  # Genbrugelige hjælpefunktioner
├── app.py                  # Hovedfil, der starter app'en og håndterer navigation
└── ...
```

## 2. Kernekoncepter

Vores arkitektur er baseret på et par vigtige designprincipper, som det er vigtigt at forstå:

*   **Konfigurationsdrevet Design:** Næsten al screeningslogik (regler, point, vægte) er defineret i JSON-filer i `config/`-mappen. Dette gør det muligt at justere eller tilføje nye strategier uden at ændre i Python-koden.

*   **Sektor-Normalisering:** For at sikre en fair sammenligning af nøgletal på tværs af forskellige brancher (f.eks. en bank vs. en tech-virksomhed), anvender vi en avanceret normaliserings-algoritme, der vurderer hver aktie i forhold til dens konkurrenter i samme sektor.

*   **Modulær Værdiansættelse:** Værdiansættelses-motoren er en selvstændig komponent, der udfører en komplet fundamental analyse ved hjælp af anerkendte finansielle modeller som Discounted Cash Flow (DCF) og WACC.

*   **Robust Datahåndtering:** Al ekstern datakommunikation sker gennem en centraliseret API-klient, der implementerer aggressiv caching for ydeevne og en fallback-mekanisme for at sikre høj oppetid.

## 3. Dybdegående Teknisk Dokumentation

For en detaljeret, teknisk gennemgang af implementeringen af hvert enkelt kernemodul – inklusiv specifikke algoritmer, klasse-interaktioner og designvalg – henvises til vores fulde tekniske dokumentationsbibliotek i `docs/`-mappen:

*   **[Teknisk Oversigt](./docs/00_OVERVIEW.md)**
*   **[1. Konfiguration og Dataloading](./docs/01_CONFIG_AND_DATA_LOADING.md)**
*   **[2. API Klient](./docs/02_API_CLIENT.md)**
*   **[3. Screenings-motor](./docs/03_SCREENING_ENGINE.md)**
*   **[4. Værdiansættelses-motor](./docs/04_VALUATION_ENGINE.md)**
*   **[5. UI Implementering](./docs/05_UI_IMPLEMENTATION.md)**
*   **[6. Værktøjer og Hjælpefunktioner](./docs/06_UTILITIES.md)**

## 4. Kom Godt i Gang

For at opsætte projektet på din lokale maskine og køre det, følg venligst installationsguiden:

*   **[Installationsguide](./INSTALLATION.md)**