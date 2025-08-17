# core/screening/multibagger_screener.py

import json
from core.config_loader import load_multibagger_profiles

# Hent profilerne (Stram, Løs, Momentum)
PROFILES = load_multibagger_profiles()

def screen_stocks(stock_data, profile_name):
    """
    Screen en enkelt aktie baseret på en given profil.
    Returnerer (score, passes) hvor 'passes' er en boolean.
    """
    profile = PROFILES.get(profile_name)
    if not profile:
        raise ValueError(f"Ukendt profil: {profile_name}")

    score = 0
    total_weight = 0
    passed_filters = 0
    total_filters = len(profile["filters"])

    # Gennemløb hvert filter i profilen
    for filter_name, criteria in profile["filters"].items():
        weight = criteria.get("weight", 1)
        total_weight += weight

        # Hent værdi fra stock_data
        data_key = criteria.get("data_key")
        operator = criteria.get("operator")
        value = criteria.get("value")
        data_value = stock_data.get(data_key)

        # Hvis data mangler, tæller det ikke
        if data_value is None:
            continue

        # Evaluer betingelsen
        passed = False
        try:
            if operator == "gt":
                passed = data_value > value
            elif operator == "lt":
                passed = data_value < value
            elif operator == "gte":
                passed = data_value >= value
            elif operator == "lte":
                passed = data_value <= value
            elif operator == "eq":
                passed = data_value == value
            elif operator == "between":
                passed = value[0] <= data_value <= value[1]
        except Exception as e:
            print(f"Fejl ved evaluering af filter {filter_name} for {data_key}: {e}")
            continue

        if passed:
            score += weight
            passed_filters += 1

    # Beregn samlet score i procent
    final_score = (score / total_weight * 100) if total_weight > 0 else 0

    # Afgør om aktien "passer" baseret på minimum score
    passes = final_score >= profile.get("min_score", 70)

    return final_score, passes