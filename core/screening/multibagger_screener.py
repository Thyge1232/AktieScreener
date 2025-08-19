import pandas as pd
from config_loader import load_region_mappings
# RETTET IMPORT: Importerer nu fra den nye, neutrale utils.py
from .utils import evaluate_condition, evaluate_range_filter, evaluate_scaled_filter

# --- FJERNET: Alle evaluate_... funktioner er nu flyttet til utils.py ---

# --- Hovedfunktion til Multibagger Screening (Uændret) ---
def screen_stocks(df, profile_name, config, selected_regions=None, dynamic_weights=None):
    """
    Screener aktier baseret på Multibagger-profiler, regioner og dynamiske vægte fra UI.
    Håndterer grundlæggende filtertyper: 'binary', 'range', 'scaled'.
    """
    region_mappings = load_region_mappings()
    profiles = config # Antager config er selve profildata
    profile = profiles.get(profile_name)

    if not profile:
        print(f"[ERROR] Profil '{profile_name}' ikke fundet i konfigurationen.")
        return pd.DataFrame()

    pre_filters = profile.get('pre_filters', {})
    filters = profile.get('filters', {})
    min_score = profile.get('min_score', 0)

    df_results = df.copy()
    print(f"[DEBUG] [Multibagger Screener] Starter screening med {len(df_results)} aktier.")

    # 1. Anvend regions-filter
    if selected_regions:
        countries_to_include = {country for region in selected_regions for country in region_mappings.get(region, [])}
        if 'Country' in df_results.columns and countries_to_include:
            countries_lower = {c.lower() for c in countries_to_include}
            df_results = df_results[df_results['Country'].fillna('').str.lower().isin(countries_lower)]
            print(f"[DEBUG] [Multibagger Screener] Efter UI region filter: {len(df_results)} aktier tilbage.")

    # 2. Anvend pre_filters fra JSON
    for filter_name, pre_filter_details in pre_filters.items():
        data_key = pre_filter_details['data_key']
        series_to_check = df_results.get(data_key)
        if series_to_check is not None:
            # Sørg for at håndtere tomme serier efter filtrering
            if not df_results.empty:
                condition_met = series_to_check.apply(lambda x: evaluate_condition(x, pre_filter_details['operator'], pre_filter_details['value']))
                df_results = df_results[condition_met]
                print(f"[DEBUG] [Multibagger Screener] Efter pre-filter '{filter_name}': {len(df_results)} aktier tilbage.")

    if df_results.empty:
        return pd.DataFrame()

    df_results = df_results.reset_index(drop=True)

    # ✅ Initialiser score-kolonner til nedbrydning
    for filter_name in filters.keys():
        df_results[f"points_{filter_name}"] = 0.0

    df_results['Score'] = 0.0

    # 3. Beregn den maksimale mulige score baseret på DYNAMISKE vægte
    max_possible_score = sum(dynamic_weights.values()) if dynamic_weights else 0
    print(f"[DEBUG] [Multibagger Screener] Maksimal mulig score (dynamisk): {max_possible_score}")
    if max_possible_score == 0:
        df_results['Score_Percent'] = 0
        return df_results

    # 4. Anvend scorings-filtre
    for filter_name, filter_details in filters.items():
        data_key = filter_details['data_key']
        filter_type = filter_details['type']

        series_to_check = df_results.get(data_key)

        if series_to_check is not None:
            raw_points = pd.Series([0.0] * len(df_results), index=df_results.index)

            if filter_type == 'range':
                max_val = max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=1)
                if max_val > 0:
                    raw_points = series_to_check.apply(lambda x: evaluate_range_filter(x, filter_details['ranges']) / max_val)
            elif filter_type == 'scaled':
                max_val = max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))
                if max_val > 0:
                    kwargs = {k: v for k, v in filter_details.items() if k in ['min_value', 'max_value', 'target_min', 'target_max']}
                    raw_points = series_to_check.apply(lambda x: evaluate_scaled_filter(x, **kwargs) / max_val)

            current_weight = dynamic_weights.get(filter_name, 0)
            weighted_points = raw_points * current_weight

            df_results[f"points_{filter_name}"] = weighted_points
            df_results['Score'] += weighted_points

    # 5. Finaliser og returner resultater
    df_results['Score_Percent'] = (df_results['Score'] / max_possible_score) * 100
    df_filtered = df_results[df_results['Score_Percent'] >= min_score]
    df_sorted = df_filtered.sort_values(by='Score_Percent', ascending=False)

    display_columns = ['Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Market Cap', 'Price', 'Score_Percent']
    metric_columns = list(set(f['data_key'] for f in filters.values()))
    final_display_columns = display_columns[:6] + metric_columns + display_columns[6:]
    existing_columns = [col for col in final_display_columns if col in df_sorted.columns]

    return df_sorted[existing_columns + [col for col in df_sorted.columns if col.startswith('points_')]]