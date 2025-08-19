import pandas as pd

# --- Funktioner til evaluering af filtre ---

def evaluate_condition(row_value, operator, condition_value):
    """Evaluerer en binær betingelse."""
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
    """Evaluerer en range-baseret filter."""
    if pd.isna(row_value):
        return 0.0
    
    for range_def in ranges:
        min_val, max_val = range_def.get('min'), range_def.get('max')
        points = range_def.get('points', 0.0)
        
        is_in_range = False
        if min_val is None and max_val is not None:
            if row_value < max_val: is_in_range = True
        elif min_val is not None and max_val is None:
            if row_value >= min_val: is_in_range = True
        elif min_val is not None and max_val is not None:
            if min_val <= row_value < max_val: is_in_range = True
        
        if is_in_range:
            return float(points)
    return 0.0

def evaluate_scaled_filter(row_value, min_value, max_value, target_min, target_max):
    """Evaluerer en lineært scaled filter."""
    if pd.isna(row_value):
        return 0.0

    clamped_value = max(min_value, min(max_value, row_value))
    
    if max_value == min_value:
        return float(target_min)
    
    ratio = (clamped_value - min_value) / (max_value - min_value)
    points = target_min + ratio * (target_max - target_min)
    return float(points)