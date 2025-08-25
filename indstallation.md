

---

# 🔧 Installationsguide til Investment Screener

Denne guide beskriver, hvordan du sætter projektet op på din lokale maskine fra start til slut.

## Forudsætninger

*   **Python:** Du skal have Python 3.8 eller nyere installeret. Du kan downloade det fra [python.org](https://www.python.org/).
*   **Git:** Nødvendigt for at klone projektkoden. Du kan downloade det fra [git-scm.com](https://git-scm.com/).
*   **Adgang til en terminal/kommandoprompt.**

## Trin-for-trin Installation

### 1. Klon Repositoriet

Åbn din terminal, naviger til den mappe, hvor du vil gemme projektet, og kør følgende kommando:
```bash
git clone <din-repository-url>
cd <repository-mappe>
```

### 2. Opret et Virtuelt Miljø (Stærkt Anbefalet)

For at isolere projektets afhængigheder og undgå konflikter med andre Python-projekter, bør du oprette et virtuelt miljø.

```bash
# Opret et miljø i en mappe ved navn .venv
python -m venv .venv

# Aktiver miljøet
# På Windows:
.venv\Scripts\activate
# På macOS/Linux:
source .venv/bin/activate
```**Vigtigt:** Sørg for, at dit virtuelle miljø er aktivt for alle efterfølgende kommandoer. Du vil typisk se `(.venv)` i starten af din kommandolinje.

### 3. Installer Nødvendige Pakker

Projektet afhænger af en række tredjepartsbiblioteker. Opret en fil ved navn `requirements.txt` i projektets rod med følgende indhold:

```
# requirements.txt
streamlit
pandas
numpy
plotly
streamlit-aggrid
yfinance
```

Installér derefter alle pakkerne på én gang ved at køre:
```bash
pip install -r requirements.txt
```

### 4. Konfiguration af API-nøgle (Valgfrit)

Funktionerne til **værdiansættelse** kræver en API-nøgle fra **Alpha Vantage**. Hvis du kun vil bruge screener-delen, kan du springe dette trin over.

1.  Få en gratis API-nøgle på [alphavantage.co](https://www.alphavantage.co/support/#api-key).
2.  I roden af dit projekt, opret en mappe ved navn `.streamlit`.
3.  Inde i `.streamlit`-mappen, opret en fil ved navn `secrets.toml`.
4.  Tilføj følgende linje til `secrets.toml` og erstat med din egen nøgle:

    ```toml
    ALPHA_VANTAGE_API_KEY = "DIN_API_NØGLE_HER"
    ```

### 5. Klargør Konfigurationsfiler

Applikationens screeningslogik er styret af JSON-filer. Sørg for, at den korrekte mappestruktur findes i projektets rod, og at de medfølgende JSON-filer er placeret korrekt:

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

### 6. Klargøring af Datafil

Applikationen er designet til at fungere med data eksporteret fra [Finviz.com](https://finviz.com/screener.ashx).

1.  Gå til Finviz' screener.
2.  Vælg de kolonner/data, du ønsker at screene på. **VIGTIGT:** Sørg for at inkludere de kolonner, som dine screeningsprofiler kræver (f.eks. `PEG`, `ROIC`, `Total Debt/Equity`).
3.  Klik på "Export" nederst til højre for at downloade en CSV-fil.
4.  Placer den downloadede CSV-fil i **roden** af projektmappen.

**Bemærk:** Hvis der er mere end én CSV-fil i mappen, vil applikationen vise en fejl. Sørg for kun at have én datafil ad gangen.

## Kør Applikationen

Når alle ovenstående trin er fuldført, kan du starte applikationen fra din terminal:

```bash
streamlit run app.py
```
Streamlit vil starte en lokal webserver og åbne applikationen i din standardbrowser.

## Fejlfinding

*   **`ModuleNotFoundError`**: Dette betyder typisk, at dit virtuelle miljø ikke er aktivt, eller at `pip install -r requirements.txt` ikke blev kørt korrekt. Prøv at aktivere miljøet igen og køre installationskommandoen.
*   **Fejl ved indlæsning af konfigurationsfil**: Dobbelttjek, at `config`-mappen og dens undermapper er stavet korrekt og ligger i projektets rod.
*   **API-nøgle virker ikke**: Sørg for, at filen hedder `secrets.toml` (ikke `.txt`) og er placeret korrekt i `.streamlit`-mappen.