import pandas as pd
import numpy as np
from config_loader import load_region_mappings
from .utils import evaluate_condition, evaluate_range_filter, evaluate_scaled_filter


class SectorNormalizer:
    """Robust sektor-normalisering med caching af sektorstatistik."""
    
    def __init__(self, df):
        self.sector_stats_cache = {}
        self._precompute_sector_stats(df)
    
    def _precompute_sector_stats(self, df):
        """Cache sektorstatistik for alle numeriske kolonner."""
        if 'Sector' not in df.columns:
            return
            
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col in df.columns and not df[col].isna().all():
                self.sector_stats_cache[col] = df.groupby('Sector')[col].agg(['median', 'std', 'count'])
    
    def normalize_by_percentile(self, series, sector_series, is_inverse_metric=False):
        """
        Percentil-baseret normalisering indenfor sektor.
        Returnerer værdi i range 0-2, hvor 1 = median.
        """
        if series.name not in self.sector_stats_cache:
            return pd.Series([1.0] * len(series), index=series.index)
        
        def sector_percentile_rank(group):
            if len(group) < 2:  # Mindst 2 datapunkter for meaningsfuld percentil
                return pd.Series([0.5] * len(group), index=group.index)
            return group.rank(pct=True, method='average')
        
        try:
            percentiles = series.groupby(sector_series, group_keys=False).apply(sector_percentile_rank)
            
            if is_inverse_metric:
                # Lavere værdi = bedre, så inverter percentiler
                normalized = 2 * (1 - percentiles)
            else:
                # Højere værdi = bedre
                normalized = 2 * percentiles
                
            return normalized.fillna(1.0).clip(0, 2)
            
        except Exception:
            # Fallback ved fejl
            return pd.Series([1.0] * len(series), index=series.index)
    
    def normalize_by_zscore(self, series, sector_series, is_inverse_metric=False):
        """
        Z-score baseret normalisering som alternativ.
        """
        if series.name not in self.sector_stats_cache:
            return pd.Series([1.0] * len(series), index=series.index)
        
        stats = self.sector_stats_cache[series.name]
        sector_medians = sector_series.map(stats['median'])
        sector_stds = sector_series.map(stats['std'])
        
        # Håndter sektorer uden tilstrækkelig variation
        valid_std = sector_stds > 0
        z_scores = pd.Series([0.0] * len(series), index=series.index)
        z_scores[valid_std] = (series[valid_std] - sector_medians[valid_std]) / sector_stds[valid_std]
        
        if is_inverse_metric:
            z_scores = -z_scores
        
        # Konverter til 0-2 skala med 1 som median
        normalized = 1 + (z_scores / 3)
        return normalized.fillna(1.0).clip(0, 2)


def evaluate_percentile_range_filter(row_value, series_to_check, ranges):
    """Evaluerer range-filter baseret på percentiler."""
    if pd.isna(row_value):
        return 0.0
    
    # Cache percentiler for efficiency
    percentiles = {}
    for range_def in ranges:
        for key in ['min', 'max']:
            if key in range_def and range_def[key] is not None:
                pct_val = range_def[key]
                if pct_val not in percentiles:
                    percentiles[pct_val] = series_to_check.quantile(pct_val / 100)
    
    for range_def in ranges:
        min_percentile = range_def.get('min')
        max_percentile = range_def.get('max')
        points = range_def.get('points', 0.0)
        
        min_val = percentiles.get(min_percentile) if min_percentile is not None else None
        max_val = percentiles.get(max_percentile) if max_percentile is not None else None
        
        # Check if value falls in range
        in_range = True
        if min_val is not None and row_value < min_val:
            in_range = False
        if max_val is not None and row_value >= max_val:
            in_range = False
        
        if in_range:
            return float(points)
    
    return 0.0


def evaluate_hybrid_range_scaled_filter(row_value, ranges):
    """Evaluerer hybrid range & scaled filter med bedre fejlhåndtering."""
    if pd.isna(row_value):
        return 0.0
    
    for range_def in ranges:
        min_val = range_def.get('min')
        max_val = range_def.get('max')
        
        # Check if in range
        in_range = True
        if min_val is not None and row_value < min_val:
            in_range = False
        if max_val is not None and row_value >= max_val:
            in_range = False
        
        if in_range:
            base_points = range_def.get('base_points', 0)
            scaled_points = range_def.get('scaled_points', 0)
            
            # Calculate scaled component
            if min_val is not None and max_val is not None and min_val != max_val:
                ratio = (row_value - min_val) / (max_val - min_val)
                ratio = max(0, min(1, ratio))  # Clamp ratio to [0,1]
                scaled_component = scaled_points * ratio
            else:
                scaled_component = scaled_points
            
            return float(base_points + scaled_component)
    
    return 0.0


def apply_normalization(df, filter_details, normalizer):
    """Anvender normalisering på en serie baseret på filter konfiguration."""
    data_key = filter_details['data_key']
    normalization = filter_details.get('normalization')
    
    series = df.get(data_key)
    if series is None or 'Sector' not in df.columns:
        return series
    
    if normalization == "sector_median_relative":
        return normalizer.normalize_by_percentile(series, df['Sector'], is_inverse_metric=False)
    elif normalization == "sector_median_relative_inverse":
        return normalizer.normalize_by_percentile(series, df['Sector'], is_inverse_metric=True)
    
    return series


def screen_stocks_value(df, profile_name, config, selected_regions=None, dynamic_weights=None):
    """
    Hovedfunktion til Value screening med forbedret normalisering.
    """
    region_mappings = load_region_mappings()
    profile = config.get(profile_name)
    
    if not profile:
        print(f"[ERROR] Profil '{profile_name}' ikke fundet.")
        return pd.DataFrame()
    
    df_results = df.copy()
    normalizer = SectorNormalizer(df_results)
    
    print(f"[DEBUG] Starter med {len(df_results)} aktier.")
    
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
            print(f"[DEBUG] Efter region filter: {len(df_results)} aktier.")
    
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
            print(f"[DEBUG] Efter pre-filter '{filter_name}': {len(df_results)} aktier.")
    
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
    
    print(f"[DEBUG] Max mulig score: {max_possible_score}")
    
    # 4. Anvend scoring filters med forbedret normalisering
    for filter_name, filter_details in filters.items():
        # Anvend normalisering først
        series_to_check = apply_normalization(df_results, filter_details, normalizer)
        
        if series_to_check is None:
            continue
        
        filter_type = filter_details['type']
        boundary_type = filter_details.get('boundary_type')
        
        # Beregn rå points
        raw_points = pd.Series([0.0] * len(df_results), index=df_results.index)
        
        if filter_type == 'range':
            if boundary_type == 'percentile':
                max_val = max((r.get('points', 0) for r in filter_details['ranges']), default=1)
                if max_val > 0:
                    raw_points = series_to_check.apply(
                        lambda x: evaluate_percentile_range_filter(
                            x, series_to_check, filter_details['ranges']
                        ) / max_val
                    )
            else:
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
        
        elif filter_type == 'hybrid_range_scaled':
            max_possible = max(
                (r.get('base_points', 0) + r.get('scaled_points', 0) 
                 for r in filter_details.get('ranges', [])), 
                default=1
            )
            if max_possible > 0:
                raw_points = series_to_check.apply(
                    lambda x: evaluate_hybrid_range_scaled_filter(
                        x, filter_details['ranges']
                    ) / max_possible
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
    display_columns = [
        'Ticker', 'Company', 'Sector', 'Industry', 'Country', 
        'Market Cap', 'Price', 'Score_Percent'
    ]
    metric_columns = list(set(f['data_key'] for f in filters.values()))
    final_columns = display_columns[:6] + metric_columns + display_columns[6:]
    
    existing_columns = [col for col in final_columns if col in df_sorted.columns]
    point_columns = [col for col in df_sorted.columns if col.startswith('points_')]
    
    return df_sorted[existing_columns + point_columns]