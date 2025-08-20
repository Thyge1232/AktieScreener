# Filnavn: core/screening/utils.py

import pandas as pd
import numpy as np

# --- 1. Generelle Evalueringsfunktioner (fra din oprindelige utils.py + nye) ---

def evaluate_condition(row_value, operator, condition_value):
    """Evaluerer en binær betingelse (bruges i pre-filters)."""
    try:
        if pd.isna(row_value):
            return False
        if operator == "eq":
            if isinstance(row_value, str):
                return row_value.strip().lower() == str(condition_value).strip().lower()
            return row_value == condition_value
        elif operator == "between":
            return condition_value[0] <= row_value <= condition_value[1]
        elif operator == "gt": return row_value > condition_value
        elif operator == "gte": return row_value >= condition_value
        elif operator == "lt": return row_value < condition_value
        elif operator == "lte": return row_value <= condition_value
        else:
            return False
    except (TypeError, ValueError):
        return False

def evaluate_range_filter(row_value, ranges):
    """Evaluerer et simpelt range-baseret filter."""
    if pd.isna(row_value):
        return 0.0
    
    for range_def in ranges:
        min_val, max_val = range_def.get('min'), range_def.get('max')
        points = range_def.get('points', 0.0)
        
        in_range = False
        if min_val is None and max_val is not None:
            if row_value < max_val: in_range = True
        elif min_val is not None and max_val is None:
            if row_value >= min_val: in_range = True
        elif min_val is not None and max_val is not None:
            if min_val <= row_value < max_val: in_range = True
        
        if in_range:
            return float(points)
    return 0.0

def evaluate_scaled_filter(row_value, min_value, max_value, target_min, target_max):
    """Evaluerer et lineært skaleret filter."""
    if pd.isna(row_value):
        return 0.0

    clamped_value = max(min_value, min(max_value, row_value))
    
    if max_value == min_value:
        return float(target_min)
    
    ratio = (clamped_value - min_value) / (max_value - min_value)
    points = target_min + ratio * (target_max - target_min)
    return float(points)

def evaluate_percentile_range_filter(row_value, series_to_check, ranges):
    """Evaluerer et range-filter baseret på percentiler af en hel serie."""
    if pd.isna(row_value):
        return 0.0
    
    percentiles = {}
    for range_def in ranges:
        for key in ['min', 'max']:
            if key in range_def and range_def[key] is not None:
                pct_val = range_def[key]
                if pct_val not in percentiles:
                    percentiles[pct_val] = series_to_check.quantile(pct_val / 100)
    
    for range_def in ranges:
        min_p, max_p = range_def.get('min'), range_def.get('max')
        points = range_def.get('points', 0.0)
        
        min_val = percentiles.get(min_p) if min_p is not None else -np.inf
        max_val = percentiles.get(max_p) if max_p is not None else np.inf
        
        if min_val <= row_value < max_val:
            return float(points)
    return 0.0

def evaluate_hybrid_range_scaled_filter(row_value, ranges):
    """Evaluerer et hybrid range & skaleret filter."""
    if pd.isna(row_value):
        return 0.0
    
    for range_def in ranges:
        min_val, max_val = range_def.get('min'), range_def.get('max')
        
        in_range = False
        if min_val is None and max_val is not None:
            if row_value < max_val: in_range = True
        elif min_val is not None and max_val is None:
            if row_value >= min_val: in_range = True
        elif min_val is not None and max_val is not None:
            if min_val <= row_value < max_val: in_range = True
        
        if in_range:
            base_points = range_def.get('base_points', 0)
            scaled_points = range_def.get('scaled_points', 0)
            
            if min_val is not None and max_val is not None and min_val != max_val:
                ratio = (row_value - min_val) / (max_val - min_val)
                ratio = max(0, min(1, ratio))
                scaled_component = scaled_points * ratio
            else:
                scaled_component = 0 # Ingen skalering hvis intervallet er åbent
            
            return float(base_points + scaled_component)
    return 0.0

# --- 2. Sektor Normaliseringslogik ---

class SectorNormalizer:
    """Robust sektor-normalisering med caching af sektorstatistik."""
    
    def __init__(self, df):
        self.sector_stats_cache = {}
        if 'Sector' in df.columns:
            self._precompute_sector_stats(df)
    
    def _precompute_sector_stats(self, df):
        numeric_cols = df.select_dtypes(include=np.number).columns
        for col in numeric_cols:
            if not df[col].isna().all():
                # Vi cacher kun median for percentil-rangering
                self.sector_stats_cache[col] = df.groupby('Sector')[col].median()
    
    def normalize_by_percentile(self, series, sector_series, is_inverse_metric=False):
        """Percentil-baseret normalisering indenfor sektor (0-2 skala)."""
        if series.name not in self.sector_stats_cache:
            return pd.Series([1.0] * len(series), index=series.index)
        
        def sector_percentile_rank(group):
            if len(group) < 2:
                return pd.Series([0.5] * len(group), index=group.index)
            return group.rank(pct=True, method='average')
        
        try:
            percentiles = series.groupby(sector_series, group_keys=False).apply(sector_percentile_rank)
            
            if is_inverse_metric:
                normalized = 2 * (1 - percentiles)
            else:
                normalized = 2 * percentiles
                
            return normalized.fillna(1.0).clip(0, 2)
        except Exception as e:
            print(f"Error during percentile normalization for {series.name}: {e}")
            return pd.Series([1.0] * len(series), index=series.index)

# --- 3. Bindeled mellem Screener og Normalizer ---

def apply_normalization(df, filter_details, normalizer):
    """Anvender normalisering på en serie baseret på filter konfiguration."""
    data_key = filter_details['data_key']
    normalization = filter_details.get('normalization')
    
    series = df.get(data_key)
    if series is None or 'Sector' not in df.columns or not normalization:
        return series
    
    is_inverse = normalization == "sector_median_relative_inverse"
    return normalizer.normalize_by_percentile(series, df['Sector'], is_inverse_metric=is_inverse)