# 📖 Brugervejledning til Investment Screener

Denne guide forklarer trin for trin, hvordan du bruger alle funktionerne i den avancerede Investment Screener-applikation.

## 1. Start og Indlæsning af Data

Når du starter applikationen (`streamlit run app.py`), vil den automatisk forsøge at finde og indlæse en CSV-fil fra projektmappen.
*   **Automatisk Indlæsning:** Applikationen scanner rodmappen efter en CSV-fil og indlæser den. En succesmeddelelse på forsiden vil vise antallet af indlæste aktier og filnavnet.
*   **Manuel Upload:** Hvis der ikke findes en fil, eller du vil bruge en anden, kan du uploade en via "Upload Finviz CSV-fil"-knappen på forsiden. Data caches automatisk for hurtigere indlæsning næste gang.

> **Tip:** Eksporter din "Screener" fra [Finviz.com](https://finviz.com/screener.ashx) for at få den bedste oplevelse.

## 2. Navigation

Al navigation foregår i **sidepanelet** til venstre. Dette panel er din kontrolcenter gennem hele applikationen.
*   **Skift Side:** Brug dropdown-menuen "Vælg en side" til at navigere mellem `Hjem`, `Value Screener`, `Multibagger Finder`, `Mine Favoritter` og `Detaljeret Værdiansættelse`.
*   **Global Status:** Under navigationen ser du altid en statusopsummering med antallet af indlæste aktier og antallet af gemte favoritter. Dette giver dig et hurtigt overblik.
*   **Cache Management:** Knappen **"Ryd Data Cache"** er nyttig, hvis du har opdateret din underliggende CSV-fil og vil tvinge applikationen til at genindlæse og behandle den igen.

## 3. Brug af Screeners (`Value` & `Multibagger`)

De to screenere (`Value Screener` og `Multibagger Finder`) er applikationens hjerte. De fungerer efter samme princip men anvender forskellige, konfigurationsdrevne strategier.

### Trin 1: Vælg en foruddefineret Strategi og Region
*   **Screeningsprofil:** Vælg den strategi, du vil køre, fra dropdown-menuen "Vælg screeningsprofil" (f.eks., "Kvalitet (Quality Value)" eller "Deep Value"). En beskrivelsestekst under overskriften forklarer strategiens logik og formål.
*   **Geografisk Fokus:** Brug multiselect-menuen "Vælg region(er)" for at filtrere aktierne efter deres geografiske placering (f.eks., "North America", "EU & UK"). Dette er baseret på mappinger i `region_mappings.json`.

### Trin 2: Finjuster med Avancerede Vægtindstillinger
*   **Aktiver Avanceret Tilstand:** Slå funktionen **"Vis avancerede indstillinger"** til. Dette afslører den virkelige styrke og fleksibilitet i screeningsmotoren.
*   **Justér Dynamiske Vægte:** Der vises nu en række skydere – én for hvert finansielt nøgletal (kriterium) i den valgte profil.
    *   Træk i en skyder for at øge eller mindske **vægten** (dets relative betydning) i den endelige scoreberegning.
    *   Hold musen over et nøgletal for at se en **tooltip** med en detaljeret forklaring på, hvad det måler og hvordan det scorer.
*   **Historik til Undo/Redo:** Applikationen husker dine vægtjusteringer. Brug **"Fortryd"** og **"Gendan"** knapperne til at navigere mellem dine tidligere tilstande uden at miste dine indstillinger.

### Trin 3: Analyser og Interager med Resultaterne
Resultatet af din screening vises i en højt interaktiv **AgGrid-tabel**, der er fyldt med funktioner:

*   **Forstå Scoren:** Den vigtigste kolonne er **Score (%)**, som viser, hvor godt hver enkelt aktie matcher dine (vægtede) kriterier. Sorter efter denne kolonne for at se de bedste kandidater først.
*   **Filtrer Yderligere:** Brug de indbyggede filtre i AgGrid-tabellens header (over hver kolonne) til at indsnævre resultaterne. F.eks. kan du filtrere for kun at se aktier med en score over 80% eller inden for en bestemt sektor.
*   **Administrer Favoritter:** Klik på `➕`-ikonet i "⭐"-kolonnen for at tilføje en aktie til din favoritliste. Ikonet skifter til en fuld stjerne (`⭐`) for at indikere, at den er gemt. Klik på stjernen igen for at fjerne den. Denne handling gemmes øjeblikkeligt.
*   **Hent Flere Oplysninger:** Klik på en akties **ticker-symbol** (f.eks., "AAPL") for at åbne dens detaljerede side på Finviz.com i en ny browserfane. Dette giver dig mulighed for en hurtig, visuel due diligence.

## 4. Fra Screening til Dybdegående Analyse: Favoritter & Værdiansættelse

Dette afsnit beskriver det anbefalede workflow for at tage en lovende aktie fra en screening og gennemføre en fuld fundamental analyse på den.

### Trin 1: Gem Interessante Kandidater som Favoritter
Mens du gennemgår resultaterne i en screener, er den hurtigste handling at klikke på `➕`-ikonet for enhver aktie, du finder interessant. Den tilføjes øjeblikkeligt til din persistente favoritliste, som gemmes på fil (`favorites.txt`) og er tilgængelig på tværs af alle sider og sessioner.

### Trin 2: Gå til "Mine Favoritter" for et Samlet Overblik
Naviger til siden **"⭐ Mine Favoritter"** via sidepanelet. Her får du et centraliseret overblik over alle dine udvalgte aktier.

*   **Hent Live Data:** Klik på knappen `🔄 Opdater Live Data` for at hente de allerseneste **live-markedspriser** og opdaterede nøgletal for hele din favoritportefølje. Dette giver dig et øjebliksbillede af den nuværende performance.
*   **Fjern Favoritter:** Du kan fjerne aktier fra listen direkte fra tabellen ved at klikke på `⭐`-ikonet.
*   **Porteføljestatistik:** Sidepanelet på denne side viser en hurtig statistisk opsummering af din samlede favoritliste, såsom gennemsnitlig P/E, Market Cap m.m.

### Trin 3: Udfør en Fundamental Værdiansættelse
Når du har identificeret de mest spændende kandidater, er det tid til en dybdegående analyse. Gå til siden **"🎯 Detaljeret Værdiansættelse"**.

1.  **Vælg Analyseobjekt(er):** Vælg en eller flere aktier fra din favoritliste i multiselect-boksen "Vælg ticker(s) for analyse".
2.  **Start Beregningerne:** Klik på `🚀 Udfør Værdiansættelse`-knappen. **Vær tålmodig!** Applikationen vil nu:
    *   Hente nyeste data fra finansielle API'er (med caching og rate limiting).
    *   Køre den avancerede `ComprehensiveValuationEngine`.
    *   Udføre DCF-modellering, beregne WACC, køre scenarieanalyse og meget mere.
    En progress bar viser status.

### Trin 4: Forstå og Fortolkningsresultaterne
Resultaterne præsenteres struktureret for at gøre kompleks finansiel modellering overskuelig.

*   **Hurtig Oversigt (Summary):** Øverst på siden vises en tabel, der sammenligner den **Nuværende Markedspris** med den beregnede **Fair Value** og beregner den potentielle **Opside/Nedside (%)**. Dette er dit hurtige signal om markedsprisen er høj eller lav ift. den fundamentale værdi.
*   **Detaljeret Analyse via Faner:** For hver aktie dykker du ned i detaljerne gennem en række faner:
    *   **Virksomhedsprofil:** Oversigt over klassificering (f.eks. "Vækstvirksomhed"), sektor, og de vigtigste finansielle nøgletal.
    *   **WACC Analyse:** Dybdegående gennemgang af beregningen af kapitalomkostningerne, som er afgørende for DCF-modellen.
    *   **DCF Analyse:** Kernen i værdiansættelsen. Se en graf over de projicerede frie pengestrømme og den underliggende antagelse om vækstprocenter.
    *   **Sammenligningsværdi (Comps):** Værdiansættelse baseret på industrimultipla (P/E, EV/EBITDA), justeret for virksomhedens vækst og rentabilitet.
    *   **Risikovurdering:** Får en kvalitativ og kvantitativ vurdering af virksomhedens risikoprofil med en samlet score (0-100) og en liste over de vigtigste identificerede risikofaktorer.