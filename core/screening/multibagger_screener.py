import pandas as pd
from config_loader import load_region_mappings
from .utils import (
    evaluate_condition, evaluate_range_filter, evaluate_scaled_filter,
    SectorNormalizer, apply_normalization
)

def screen_stocks_multibagger(df, profile_name, config, selected_regions=None, dynamic_weights=None):
    """
    Hovedfunktion til Multibagger screening med forbedret normalisering.
    """
    region_mappings = load_region_mappings()
    profile = config.get(profile_name)
    
    if not profile:
        print(f"[ERROR] Profil '{profile_name}' ikke fundet.")
        return pd.DataFrame()
    
    df_results = df.copy()
    # Initialiser normalizeren én gang med start-dataframen
    normalizer = SectorNormalizer(df_results)
    
    print(f"[DEBUG] [Multibagger] Starter med {len(df_results)} aktier.")
    
    # 1. Regions-filter
    if selected_regions:
        countries_to_include = {
            country for region in selected_regions 
            for country in region_mappings.get(region, [])
        }
        if 'Country' in df_results.columns and countries_to_include:
            countries_lower = {c.lower() for c in countries_to_include}
            df_results = df_results[
                df_results['Country'].fillna('').str.lower().isin(countries_lower)
            ]
            print(f"[DEBUG] [Multibagger] Efter region filter: {len(df_results)} aktier.")
    
    # 2. Pre-filters
    pre_filters = profile.get('pre_filters', {})
    for filter_name, pre_filter in pre_filters.items():
        series = df_results.get(pre_filter['data_key'])
        if series is not None and not df_results.empty:
            condition_met = series.apply(
                lambda x: evaluate_condition(
                    x, pre_filter['operator'], pre_filter['value']
                )
            )
            df_results = df_results[condition_met]
            print(f"[DEBUG] [Multibagger] Efter pre-filter '{filter_name}': {len(df_results)} aktier.")
    
    if df_results.empty:
        return pd.DataFrame()
    
    df_results = df_results.reset_index(drop=True)
    
    # 3. Initialiser scoring
    filters = profile.get('filters', {})
    for filter_name in filters.keys():
        df_results[f"points_{filter_name}"] = 0.0
    df_results['Score'] = 0.0
    
    max_possible_score = sum(dynamic_weights.values()) if dynamic_weights else 0
    if max_possible_score == 0:
        df_results['Score_Percent'] = 0
        return df_results
    
    print(f"[DEBUG] [Multibagger] Max mulig score: {max_possible_score}")
    
    # 4. Anvend scoring filters med forbedret normalisering
    for filter_name, filter_details in filters.items():
        # Anvend normalisering først
        series_to_check = apply_normalization(df_results, filter_details, normalizer)
        
        if series_to_check is None:
            continue
        
        filter_type = filter_details['type']
        
        # Beregn rå points (0.0 til 1.0)
        raw_points = pd.Series([0.0] * len(df_results), index=df_results.index)
        
        if filter_type == 'range':
            max_val = max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=1)
            if max_val > 0:
                raw_points = series_to_check.apply(
                    lambda x: evaluate_range_filter(x, filter_details['ranges']) / max_val
                )
        
        elif filter_type == 'scaled':
            max_val = max(
                filter_details.get('target_min', 0), 
                filter_details.get('target_max', 0)
            )
            if max_val > 0:
                kwargs = {
                    k: v for k, v in filter_details.items() 
                    if k in ['min_value', 'max_value', 'target_min', 'target_max']
                }
                raw_points = series_to_check.apply(
                    lambda x: evaluate_scaled_filter(x, **kwargs) / max_val
                )
        
        # Anvend vægtning
        current_weight = dynamic_weights.get(filter_name, 0)
        weighted_points = raw_points * current_weight
        df_results[f"points_{filter_name}"] = weighted_points
        df_results['Score'] += weighted_points
    
    # 5. Finaliser resultater
    df_results['Score_Percent'] = (df_results['Score'] / max_possible_score) * 100
    
    min_score = profile.get('min_score', 0)
    df_filtered = df_results[df_results['Score_Percent'] >= min_score]
    df_sorted = df_filtered.sort_values(by='Score_Percent', ascending=False)
    
    # Vælg kolonner til visning
    display_columns = ['Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Market Cap', 'Price', 'Score_Percent']
    metric_columns = list(set(f['data_key'] for f in filters.values()))
    final_columns = display_columns[:6] + metric_columns + display_columns[6:]
    
    existing_columns = [col for col in final_columns if col in df_sorted.columns]
    point_columns = [col for col in df_sorted.columns if col.startswith('points_')]
    
    return df_sorted[existing_columns + point_columns]