# 🔧 Installationsguide til Investment Screener

Denne guide beskriver, hvordan du sætter projektet op på din lokale maskine.

## Forudsætninger

*   **Python:** Du skal have Python 3.8 eller nyere installeret.
*   **Git:** Nødvendigt for at klone repositoriet.
*   **Adgang til en terminal/kommandoprompt.**

## Trin-for-trin Installation

### 1. Klon Repositoriet

Åbn din terminal og kør følgende kommando for at downloade projektkoden:
```bash
git clone <din-repository-url>
cd <repository-mappe>
```

### 2. Opret et Virtuelt Miljø (Anbefalet)

Det er god praksis at isolere projektets afhængigheder i et virtuelt miljø.

```bash
# Opret et miljø
python -m venv .venv

# Aktiver miljøet
# På Windows:
.venv\Scripts\activate
# På macOS/Linux:
source .venv/bin/activate
```

### 3. Installer Nødvendige Pakker

Projektet bruger en række Python-biblioteker. Opret en fil ved navn `requirements.txt` i projektets rod med følgende indhold:

```
# requirements.txt
streamlit
pandas
numpy
plotly
streamlit-aggrid
yfinance
```

Installér derefter disse pakker ved at køre:
```bash
pip install -r requirements.txt
```

### 4. Konfiguration af API-nøgle

Funktionerne til værdiansættelse og backtesting kræver en API-nøgle fra **Alpha Vantage**.

1.  Få en gratis API-nøgle på [alphavantage.co](https://www.alphavantage.co/support/#api-key).
2.  Opret en mappe ved navn `.streamlit` i roden af dit projekt.
3.  Inde i `.streamlit`-mappen, opret en fil ved navn `secrets.toml`.
4.  Tilføj følgende linje til `secrets.toml` og erstat med din egen nøgle:

    ```toml
    ALPHA_VANTAGE_API_KEY = "DIN_API_NØGLE_HER"
    ```

Streamlit vil automatisk indlæse denne nøgle, når applikationen starter.

### 5. Opret Konfigurationsmapper og -filer

Applikationens screeningslogik er styret af JSON-filer. Opret den korrekte mappestruktur i projektets rod:

1.  Opret en mappe ved navn `config`.
2.  Inde i `config`, opret to undermapper: `mappings` og `strategies`.

Din struktur skal se således ud:
```
<projekt-rod>/
├── config/
│   ├── mappings/
│   │   └── region_mappings.json
│   └── strategies/
│       ├── value_screener_profiles.json
│       └── multibagger_profiles.json
└── ... (andre filer)
```
Placer de relevante JSON-filer i disse mapper.

### 6. Klargøring af Datafil

Applikationen er designet til at fungere med data eksporteret fra [Finviz.com](https://finviz.com/screener.ashx).

1.  Gå til Finviz' screener.
2.  Vælg de kolonner/data, du ønsker at screene på. **VIGTIGT:** Sørg for at inkludere de kolonner, som dine screeningsprofiler kræver (f.eks. `PEG`, `ROIC`, `Total Debt/Equity`).
3.  Klik på "Export" nederst til højre for at downloade en CSV-fil.
4.  Placer den downloadede CSV-fil i **roden** af projektmappen.

**Bemærk:** Hvis der er mere end én CSV-fil i mappen, vil applikationen vise en fejl. Sørg for kun at have én datafil ad gangen.

## Kør Applikationen

Når alle ovenstående trin er fuldført, kan du starte applikationen:

```bash
streamlit run app.py
```