# 📖 Brugervejledning til Investment Screener

Denne guide forklarer, hvordan du bruger de forskellige funktioner i applikationen.

## 1. Start og Indlæsning af Data

Når du starter applikationen, vil den automatisk forsøge at finde og indlæse en CSV-fil fra projektmappen.
*   **Succes:** Hvis en fil findes, ser du en succesmeddelelse på forsiden med antallet af indlæste aktier.
*   **Ingen fil:** Hvis ingen fil findes, kan du uploade en direkte på forsiden via "Upload Finviz CSV-fil"-knappen.

## 2. Navigation

Al navigation foregår i **sidepanelet** til venstre.
*   **Vælg side:** Brug dropdown-menuen til at skifte mellem `Hjem`, `Value Screener`, `Multibagger Finder`, `Mine Favoritter` og `Backtesting`.
*   **Statusinformation:** Under navigationen ser du altid status for, hvor mange aktier der er indlæst, navnet på datafilen og antallet af gemte favoritter.
*   **Ryd Cache:** Knappen "Ryd Data Cache" kan bruges, hvis du har opdateret din CSV-fil og vil tvinge applikationen til at genindlæse og genbehandle den.

## 3. Brug af Screeners (`Value` & `Multibagger`)

Begge screenere fungerer på samme måde, men med forskellige strategier og kriterier.

### Trin 1: Vælg Profil og Region
*   **Screeningsprofil:** Vælg en foruddefineret strategi fra dropdown-menuen (f.eks., "Kvalitet & Værdi"). Beskrivelsen under titlen forklarer formålet med profilen.
*   **Region:** Vælg de geografiske områder, du vil inkludere i din screening (f.eks., "North America", "EU & UK").

### Trin 2: Juster Vægte (Avanceret Tilstand)
*   Slå **"Vis avancerede indstillinger"** til for at finjustere screeningsalgoritmen.
*   Der vises nu en række skydere – én for hvert finansielt nøgletal i profilen.
*   Træk i en skyder for at øge eller mindske vigtigheden (point-vægten) af det pågældende kriterium. Hold musen over et nøgletal for at se en detaljeret forklaring af, hvordan point tildeles.
*   Brug **Fortryd/Gendan** knapperne til at navigere i dine justeringer.

### Trin 3: Analyser Resultaterne
*   Resultaterne vises i en interaktiv tabel. Tabellen inkluderer en **Score** (i %), der viser, hvor godt hver aktie matcher dine kriterier.
*   **Filtrer Resultater:** Brug filtrene over tabellen til at indsnævre listen baseret på minimumsscore, sektor eller markedsstørrelse.
*   **Tilføj til Favoritter:** Klik på `➕`-ikonet i "⭐"-kolonnen for at tilføje en aktie til din favoritliste. Ikonet skifter til `⭐`. Klik igen for at fjerne den.
*   **Undersøg Aktie:** Klik på en akties ticker-symbol (f.eks., "AAPL") for at åbne dens side på Finviz i en ny fane.

## 4. Mine Favoritter

Dette er din personlige hub for de aktier, du har fundet interessante.

### Dataopdatering og Analyse
*   **Opdater Data:** Klik på denne knap for at hente de seneste live-data (pris, P/E, udbytte osv.) for alle dine favoritter via Alpha Vantage API'en.
*   **Hent Værdiansættelse:** Denne knap aktiverer en avanceret analyse af de første par aktier på din liste. Den beregner en "Fair Value" baseret på en DCF-model (Discounted Cash Flow).

### Forstå Værdiansættelsen
Når analysen er færdig, vises resultaterne i flere sektioner:
*   **Oversigt:** En tabel, der sammenligner `Current Price` med den beregnede `Fair Value` og viser den potentielle `Upside`.
*   **Detaljeret Analyse:** Klik på en aktie for at folde en detaljeret boks ud med anbefalinger (Køb/Hold/Sælg) og nøgletal som **WACC** (Weighted Average Cost of Capital).
*   **DCF Analyse (Fanen):** Visualiserer de forventede fremtidige frie pengestrømme (Free Cash Flow), der er brugt i DCF-modellen.
*   **Scenarier (Fanen):** Viser en graf med værdiansættelse i et `Best Case`, `Base Case` og `Worst Case` scenarie.

### Fjern Favoritter
Du kan fjerne en aktie fra din favoritliste ved at klikke på `⭐`-ikonet i tabellen, så det skifter tilbage til `➕`. Ændringerne gemmes automatisk.