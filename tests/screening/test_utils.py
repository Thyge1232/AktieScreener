# tests/screening/test_utils.py

import pandas as pd
import numpy as np
import pytest

# Importer de faktiske funktioner fra din utils.py fil
from core.screening.utils import (
    evaluate_condition,
    evaluate_range_filter,
    evaluate_scaled_filter
)

# --- Test for evaluate_condition ---

def test_condition_less_than_true():
    assert evaluate_condition(row_value=5, operator="lt", condition_value=10) == True

def test_condition_less_than_false():
    assert evaluate_condition(row_value=10, operator="lt", condition_value=10) == False

def test_condition_greater_than_or_equal_true():
    assert evaluate_condition(row_value=15, operator="gte", condition_value=15) == True

def test_condition_between_true():
    assert evaluate_condition(row_value=7, operator="between", condition_value=[5, 10]) == True

def test_condition_between_false_on_upper_boundary():
    # Vores 'between' er [min, max], så den er inklusiv
    assert evaluate_condition(row_value=11, operator="between", condition_value=[5, 10]) == False
    
def test_condition_string_equals_true():
    assert evaluate_condition(row_value=" Tech ", operator="eq", condition_value="tech") == True

def test_condition_handles_nan():
    assert evaluate_condition(row_value=np.nan, operator="lt", condition_value=10) == False


# --- Test for evaluate_range_filter ---

# En genbrugelig konfiguration for range-tests
RANGE_CONFIG_EXAMPLE = [
    {'min': 10, 'max': 20, 'points': 10.0},
    {'min': 20, 'max': 30, 'points': 5.0},
    {'min': None, 'max': 10, 'points': 15.0} # Håndterer "mindre end 10"
]

def test_range_filter_in_first_range():
    # Værdi 15 er i det første interval [10, 20)
    assert evaluate_range_filter(15, RANGE_CONFIG_EXAMPLE) == 10.0

def test_range_filter_on_boundary():
    # Værdi 20 er i det andet interval [20, 30)
    assert evaluate_range_filter(20, RANGE_CONFIG_EXAMPLE) == 5.0

def test_range_filter_in_open_ended_range():
    # Værdi 5 er i det tredje interval (< 10)
    assert evaluate_range_filter(5, RANGE_CONFIG_EXAMPLE) == 15.0

def test_range_filter_outside_all_ranges():
    # Værdi 35 er ikke i noget interval
    assert evaluate_range_filter(35, RANGE_CONFIG_EXAMPLE) == 0.0

def test_range_filter_handles_nan():
    assert evaluate_range_filter(np.nan, RANGE_CONFIG_EXAMPLE) == 0.0


# --- Test for evaluate_scaled_filter ---

def test_scaled_filter_at_min_boundary():
    # Ved min_value skal vi have target_min
    points = evaluate_scaled_filter(row_value=10, min_value=10, max_value=20, target_min=0, target_max=100)
    assert points == 0.0

def test_scaled_filter_at_max_boundary():
    # Ved max_value skal vi have target_max
    points = evaluate_scaled_filter(row_value=20, min_value=10, max_value=20, target_min=0, target_max=100)
    assert points == 100.0

def test_scaled_filter_at_midpoint():
    # Midt imellem input-intervallet skal give midt i output-intervallet
    points = evaluate_scaled_filter(row_value=15, min_value=10, max_value=20, target_min=0, target_max=100)
    assert points == 50.0

def test_scaled_filter_clamps_low_value():
    # En værdi under min_value klemmes fast til min_value, hvilket giver target_min
    points = evaluate_scaled_filter(row_value=5, min_value=10, max_value=20, target_min=0, target_max=100)
    assert points == 0.0

def test_scaled_filter_clamps_high_value():
    # En værdi over max_value klemmes fast til max_value, hvilket giver target_max
    points = evaluate_scaled_filter(row_value=25, min_value=10, max_value=20, target_min=0, target_max=100)
    assert points == 100.0

def test_scaled_filter_reverse_scale():
    # Tester hvor en lavere værdi er bedre (f.eks. P/E)
    # [10, 20] mappes til [100, 0]
    points = evaluate_scaled_filter(row_value=15, min_value=10, max_value=20, target_min=100, target_max=0)
    assert points == 50.0
    
    # En lav værdi (bedst) skal give høj score
    points_best = evaluate_scaled_filter(row_value=10, min_value=10, max_value=20, target_min=100, target_max=0)
    assert points_best == 100.0

def test_scaled_filter_handles_nan():
    points = evaluate_scaled_filter(row_value=np.nan, min_value=10, max_value=20, target_min=0, target_max=100)
    assert points == 0.0

def test_scaled_filter_handles_zero_range():
    # Hvis min og max er ens, skal den returnere target_min
    points = evaluate_scaled_filter(row_value=10, min_value=10, max_value=10, target_min=50, target_max=100)
    assert points == 50.0