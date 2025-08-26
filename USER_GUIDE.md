# 📖 Brugervejledning til Investment Screener

Denne guide forklarer, hvordan du bruger de forskellige funktioner i applikationen.

## 1. Start og Indlæsning af Data

Når du starter applikationen, vil den automatisk forsøge at finde og indlæse en CSV-fil fra projektmappen.
*   **Succes:** Hvis en fil findes, ser du en succesmeddelelse på forsiden med antallet af indlæste aktier.
*   **Ingen fil:** Hvis ingen fil findes, kan du uploade en direkte på forsiden via "Upload Finviz CSV-fil"-knappen.

## 2. Navigation

Al navigation foregår i **sidepanelet** til venstre.
*   **Vælg side:** Brug dropdown-menuen til at skifte mellem `Hjem`, `Value Screener`, `Multibagger Finder` og `Mine Favoritter`.
*   **Statusinformation:** Under navigationen ser du altid status for, hvor mange aktier der er indlæst, og antallet af gemte favoritter.
*   **Ryd Cache:** Knappen "Ryd Data Cache" kan bruges, hvis du har opdateret din CSV-fil og vil tvinge applikationen til at genindlæse den.

## 3. Brug af Screeners (`Value` & `Multibagger`)

Begge screenere fungerer på samme måde, men med forskellige strategier og kriterier.

### Trin 1: Vælg Profil og Region
*   **Screeningsprofil:** Vælg en foruddefineret strategi fra dropdown-menuen (f.eks., "Kvalitet (Quality Value)"). Beskrivelsen under titlen forklarer formålet med profilen.
*   **Region:** Vælg de geografiske områder, du vil inkludere i din screening (f.eks., "North America", "EU & UK").

### Trin 2: Juster Vægte (Avanceret Tilstand)
*   Slå **"Vis avancerede indstillinger"** til for at finjustere screeningsalgoritmen.
*   Der vises nu en række skydere – én for hvert finansielt nøgletal i profilen.
*   Træk i en skyder for at øge eller mindske vigtigheden (point-vægten) af det pågældende kriterium. Hold musen over et nøgletal for at se en detaljeret forklaring.
*   Brug **Fortryd/Gendan** knapperne til at navigere i dine justeringer.

### Trin 3: Analyser Resultaterne
*   Resultaterne vises i en interaktiv tabel med en **Score** (i %), der viser, hvor godt hver aktie matcher dine kriterier.
*   **Filtrer Resultater:** Brug filtrene over tabellen til at indsnævre listen baseret på minimumsscore, sektor eller markedsstørrelse.
*   **Tilføj til Favoritter:** Klik på `➕`-ikonet i "⭐"-kolonnen for at tilføje en aktie til din favoritliste. Ikonet skifter til `⭐`. Klik igen for at fjerne den.
*   **Undersøg Aktie:** Klik på en akties ticker-symbol (f.eks., "AAPL") for at åbne dens side på Finviz i en ny fane.

## 4. Fra Screening til Analyse: Favoritter & Værdiansættelse

Dette er workflowet for at tage en interessant aktie fra en screening og udføre en dybdegående analyse.

### Trin 1: Gem Favoritter
Mens du analyserer resultaterne i en screener, skal du klikke på `➕`-ikonet for alle de aktier, du vil undersøge nærmere. De gemmes nu på din personlige favoritliste.

### Trin 2: Gå til "Mine Favoritter"
Naviger til siden **"⭐ Mine Favoritter"** i sidepanelet. Her ser du en samlet liste over alle dine gemte aktier.

*   **Opdater Live Data:** Klik på knappen `🔄 Opdater Data` for at hente de seneste live-kurser og nøgletal for alle dine favoritter. Dette giver et hurtigt og aktuelt overblik.
*   **Fjern Favoritter:** Du kan fjerne en aktie fra listen ved at klikke på `⭐`-ikonet i tabellen.

### Trin 3: Udfør Dybdegående Værdiansættelse
Når du er klar til en fuld analyse, skal du navigere til siden **"🎯 Detaljeret Værdiansættelse"**.

1.  **Vælg Aktier:** Vælg en eller flere aktier fra din favoritliste i multiselect-boksen.
2.  **Udfør Analyse:** Klik på den store knap `🚀 Udfør Værdiansættelse`. Applikationen vil nu hente data og køre de komplekse beregninger. Dette kan tage et øjeblik.

### Trin 4: Forstå Analyseresultaterne
Når analysen er færdig, præsenteres resultaterne i flere sektioner:

*   **Hurtig Oversigt:** En tabel øverst på siden sammenligner den **Nuværende Pris** med den beregnede **Fair Value** og viser den potentielle **Opside**.
*   **Detaljeret Analyse (Faner):** Resultaterne for hver aktie vises i separate faner. Her kan du dykke ned i:
    *   **Virksomhedsprofil:** En oversigt over virksomhedstype, sektor og nøgletal.
    *   **WACC Analyse:** Vurdering af kapitalomkostninger (diskonteringsfaktor).
    *   **DCF Analyse:** En graf over de forventede fremtidige pengestrømme, som er kernen i værdiansættelsen.
    *   **Sammenligningsværdiansættelse:** Vurdering baseret på multipla som P/E og EV/EBITDA.
    *   **Risikovurdering:** En samlet risikoscore (0-100) baseret på finansiel og forretningsmæssig risiko.