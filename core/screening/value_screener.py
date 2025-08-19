# core/screening/value_screener.py
import pandas as pd
from config_loader import load_region_mappings
from .multibagger_screener import evaluate_condition, evaluate_range_filter, evaluate_scaled_filter # Importer grundlæggende funktioner hvis nødvendigt
import numpy as np # Sørg for at denne linje er øverst i filen

# --- Funktioner specifikt til Value Screener ---

def evaluate_percentile_range_filter(row_value, series_to_check, ranges):
    """
    Evaluerer en range-baseret filter, hvor grænserne er defineret ved percentiler.
    """
    if pd.isna(row_value):
        return 0.0

    # Beregn percentiler for hele serien (kan optimeres med caching)
    percentiles = {}
    for range_def in ranges:
        if 'min' in range_def and range_def['min'] is not None:
            percentiles[range_def['min']] = series_to_check.quantile(range_def['min'] / 100)
        if 'max' in range_def and range_def['max'] is not None:
            percentiles[range_def['max']] = series_to_check.quantile(range_def['max'] / 100)

    for range_def in ranges:
        min_percentile = range_def.get('min')
        max_percentile = range_def.get('max')
        points = range_def.get('points', 0.0)

        min_val = percentiles.get(min_percentile) if min_percentile is not None else None
        max_val = percentiles.get(max_percentile) if max_percentile is not None else None

        is_in_range = False
        # Logikken her er lidt mere kompleks end standard range, afhænger af hvordan percentil-intervallerne skal fortolkes.
        # Dette er et eksempel, der antager, at hvis min_percentile er 90, så skal værdien være >= 90. percentil.
        # Hvis max_percentile er 95, skal værdien være < 95. percentil.
        # Juster logikken efter behov.
        if min_val is not None and max_val is not None:
             if min_val <= row_value < max_val: is_in_range = True
        elif min_val is not None and max_val is None: # F.eks. 90+ percentil
             if row_value >= min_val: is_in_range = True
        elif min_val is None and max_val is not None: # F.eks. under 90 percentil
             if row_value < max_val: is_in_range = True

        if is_in_range:
            return float(points)
    return 0.0

def evaluate_hybrid_range_scaled_filter(row_value, ranges):
    """
    Evaluerer en hybrid range & scaled filter.
    Returnerer point baseret på range og derefter scaling inden for range.
    """
    if pd.isna(row_value):
        return 0.0

    for range_def in ranges:
        min_val = range_def.get('min')
        max_val = range_def.get('max')
        
        # Tjek om værdien er inden for range
        is_in_range = False
        if min_val is None and max_val is not None:
            if row_value < max_val: is_in_range = True
        elif min_val is not None and max_val is None:
            if row_value >= min_val: is_in_range = True
        elif min_val is not None and max_val is not None:
            if min_val <= row_value < max_val: is_in_range = True

        if is_in_range:
            base_points = range_def.get('base_points', 0)
            scaled_points = range_def.get('scaled_points', 0)
            # Eksempel på simpel scaling inden for range (kan forbedres)
            # Her antager vi, at pointene skaleres lineært mellem min og max værdien i range
            if min_val is not None and max_val is not None and min_val != max_val:
                 # Antag, at højere værdi giver flere scaled_points (kan vendes hvis nødvendigt)
                 # Dette eksempel giver flere point jo tættere på max_val man er.
                 ratio = (row_value - min_val) / (max_val - min_val)
                 scaled_component = scaled_points * ratio
            else:
                 scaled_component = scaled_points # Hvis range er åbent eller ens, giv fuld scaled point
            return float(base_points + scaled_component)

    return 0.0

def normalize_series_by_sector(series_to_normalize, sector_series, normalization_type):
    """
    Normaliserer en pandas Series baseret på sektorer.
    Denne funktion kan nu være simpel, fordi den modtager rene, numeriske data.
    """
    # Beregn sektormedianer. Pandas' .median() ignorerer automatisk NaN-værdier.
    sector_medians = series_to_normalize.groupby(sector_series).median()

    # Knyt medianer tilbage til den oprindelige serie
    sector_median_series = sector_series.map(sector_medians)

    if normalization_type == "sector_median_relative":
        # Returner forholdet mellem værdi og sektormedian
        normalized_series = series_to_normalize / sector_median_series
    elif normalization_type == "sector_median_relative_inverse":
        # Returner forholdet mellem sektormedian og værdi
        normalized_series = sector_median_series / series_to_normalize
    else:
        # Hvis typen ikke genkendes, returner den originale serie
        normalized_series = series_to_normalize

    # Hvis en hel sektor manglede data (resultat = NaN) eller medianen var 0,
    # så udfyld med en neutral værdi på 1.0.
    return normalized_series.fillna(1.0)

# --- Hovedfunktion til Value Screening ---
def screen_stocks_value(df, profile_name, config, selected_regions=None, dynamic_weights=None):
    """
    Screener aktier baseret på Value-profiler, regioner og dynamiske vægte fra UI.
    Håndterer avancerede filtertyper som hybrid_range_scaled, percentile ranges og sektornormalisering.
    """
    region_mappings = load_region_mappings()
    profiles = config.get('profiles', {})
    profile = profiles.get(profile_name)

    if not profile:
        print(f"[ERROR] Profil '{profile_name}' ikke fundet i konfigurationen.")
        return pd.DataFrame()

    pre_filters = profile.get('pre_filters', {})
    filters = profile.get('filters', {})
    min_score = profile.get('min_score', 0)

    df_results = df.copy()
    print(f"[DEBUG] [Value Screener] Starter screening med {len(df_results)} aktier.")

    # 1. Anvend regions-filter
    if selected_regions:
        countries_to_include = {country for region in selected_regions for country in region_mappings.get(region, [])}
        if 'Country' in df_results.columns and countries_to_include:
            countries_lower = {c.lower() for c in countries_to_include}
            df_results = df_results[df_results['Country'].fillna('').str.lower().isin(countries_lower)]
            print(f"[DEBUG] [Value Screener] Efter UI region filter: {len(df_results)} aktier tilbage.")

    # 2. Anvend pre_filters fra JSON
    for filter_name, pre_filter_details in pre_filters.items():
        data_key = pre_filter_details['data_key']
        series_to_check = df_results.get(data_key)
        if series_to_check is not None:
            condition_met = series_to_check.apply(lambda x: evaluate_condition(x, pre_filter_details['operator'], pre_filter_details['value']))
            df_results = df_results[condition_met]
            print(f"[DEBUG] [Value Screener] Efter pre-filter '{filter_name}': {len(df_results)} aktier tilbage.")

    if df_results.empty:
        return pd.DataFrame()

    df_results = df_results.reset_index(drop=True)

    # ✅ Initialiser score-kolonner til nedbrydning
    for filter_name in filters.keys():
        df_results[f"points_{filter_name}"] = 0.0

    df_results['Score'] = 0.0

    # 3. Beregn den maksimale mulige score baseret på DYNAMISKE vægte
    max_possible_score = sum(dynamic_weights.values()) if dynamic_weights else 0
    print(f"[DEBUG] [Value Screener] Maksimal mulig score (dynamisk): {max_possible_score}")
    if max_possible_score == 0:
        return df_results

    # 4. Anvend scorings-filtre
    for filter_name, filter_details in filters.items():
        data_key = filter_details['data_key']
        filter_type = filter_details['type']
        normalization = filter_details.get('normalization')
        boundary_type = filter_details.get('boundary_type')

        series_to_check = df_results.get(data_key)

        if series_to_check is not None:
            # Håndter sektornormalisering hvis specificeret
            if normalization and 'Sector' in df_results.columns:
                if normalization in ["sector_median_relative", "sector_median_relative_inverse"]:
                    series_to_check = normalize_series_by_sector(series_to_check, df_results['Sector'], normalization)
                    #print(f"[DEBUG] [Value Screener] Normaliserede '{data_key}' med '{normalization}'.")

            # Beregn de "rå" point (0-1 normaliseret score)
            raw_points = pd.Series([0.0] * len(df_results), index=df_results.index)

            # Vælg den korrekte evalueringsfunktion baseret på filtertype og boundary_type
            if filter_type == 'range':
                if boundary_type == 'percentile':
                    # Brug den nye percentile funktion
                    # Bemærk: Vi sender hele serien med for at beregne percentiler
                    raw_points = series_to_check.apply(lambda x: evaluate_percentile_range_filter(x, series_to_check, filter_details['ranges']) / max((r.get('points', 0) for r in filter_details['ranges']), default=1))
                else:
                    # Brug standard range funktion
                    max_val = max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=1)
                    if max_val > 0:
                        raw_points = series_to_check.apply(lambda x: evaluate_range_filter(x, filter_details['ranges']) / max_val)

            elif filter_type == 'scaled':
                max_val = max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))
                if max_val > 0:
                    kwargs = {k: v for k, v in filter_details.items() if k in ['min_value', 'max_value', 'target_min', 'target_max']}
                    raw_points = series_to_check.apply(lambda x: evaluate_scaled_filter(x, **kwargs) / max_val)

            elif filter_type == 'hybrid_range_scaled':
                 # Brug den nye hybrid funktion
                 # Bemærk: Denne funktion returnerer allerede point, ikke en 0-1 score.
                 # Vi skal finde den maksimale mulige point for denne filtertype for at normalisere.
                 # En tilgang er at bruge 'base_points' + 'scaled_points' fra den bedste range.
                 max_possible_points_for_filter = max(
                     (r.get('base_points', 0) + r.get('scaled_points', 0) for r in filter_details.get('ranges', [])),
                     default=1
                 )
                 if max_possible_points_for_filter > 0:
                     raw_points = series_to_check.apply(lambda x: evaluate_hybrid_range_scaled_filter(x, filter_details['ranges']) / max_possible_points_for_filter)


            # ✅ Gang de rå point med den DYNAMISKE vægt fra slideren
            current_weight = dynamic_weights.get(filter_name, 0)
            weighted_points = raw_points * current_weight

            df_results[f"points_{filter_name}"] = weighted_points
            df_results['Score'] += weighted_points

    # 5. Finaliser og returner resultater
    df_results['Score_Percent'] = (df_results['Score'] / max_possible_score) * 100
    df_filtered = df_results[df_results['Score_Percent'] >= min_score]
    df_sorted = df_filtered.sort_values(by='Score_Percent', ascending=False)

    # Vælg hvilke kolonner der skal vises i hovedtabellen
    display_columns = ['Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Market Cap', 'Price', 'Score_Percent']
    # Tilføj de unikke metrikker for den specifikke profil
    metric_columns = list(set(f['data_key'] for f in filters.values()))
    final_display_columns = display_columns[:6] + metric_columns + display_columns[6:]

    existing_columns = [col for col in final_display_columns if col in df_sorted.columns]

    return df_sorted[existing_columns + [col for col in df_sorted.columns if col.startswith('points_')]]
