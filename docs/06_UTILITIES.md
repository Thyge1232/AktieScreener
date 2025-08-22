# 6. Værktøjer og Hjælpefunktioner

Dette dokument dækker de understøttende moduler, der leverer genbrugelig funktionalitet på tværs af hele applikationen.

## Datavalidering (`utils/validation.py`)

Dette modul har til formål at forbedre applikationens robusthed ved at validere data *før* det bruges i kritiske funktioner.

*   **`validate_screening_data(df, profile_config)`:**
    -   **Formål:** At sikre, at den indlæste CSV-fil er kompatibel med den valgte screeningsprofil.
    -   **Implementering:**
        1.  Den samler et `set` af alle `data_key`'s, der kræves af profilen.
        2.  Den sammenligner dette `set` med `set(df.columns)`.
        3.  Hvis der er manglende kolonner, returneres en liste af `validation_errors`, som UI'et kan vise på en brugervenlig måde, og screeningen afbrydes.
        4.  Den tjekker også for kolonner med en meget høj procentdel af manglende værdier (`NaN`) og returnerer en liste af `warnings`, som kan vises i en `st.expander`.

## Favoritstyring (`core/favorites_manager.py`)

Dette er et simpelt, men vigtigt modul, der håndterer persistens af brugerens favoritter mellem sessioner.

*   **`load_favorites()`:**
    -   Tjekker, om `favorites.txt`-filen eksisterer.
    -   Hvis den gør, læser den hver linje, fjerner whitespace (`strip()`) og returnerer en liste af ticker-strenge.
    -   Hvis ikke, returnerer den en tom liste.

*   **`save_favorites(tickers)`:**
    -   Åbner `favorites.txt` i skrive-tilstand (`'w'`), hvilket overskriver den eksisterende fil.
    -   Itererer gennem listen af tickers og skriver hver ticker til filen efterfulgt af et linjeskift (`\n`).

*   **Designvalg:**
    -   **Tekstfil vs. Database:** En simpel tekstfil blev valgt, fordi den er let, kræver ingen eksterne afhængigheder (som en database), er let for mennesker at læse og redigere, og er fuldt ud tilstrækkelig til at gemme en simpel liste af strenge.