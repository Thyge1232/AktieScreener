# config_loader.py
import json
import os
import streamlit as st

# Få den nuværende arbejdsmappe, som Streamlit sætter til projektets rod.
# Dette er den mest pålidelige metode.
PROJECT_ROOT = os.getcwd()
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')

@st.cache_data
def load_config(file_path):
    """Indlæser en JSON-konfigurationsfil fra config-mappen."""
    full_path = os.path.join(CONFIG_DIR, file_path)

    if not os.path.exists(full_path):
        st.error(f"FATAL FEJL: Konfigurationsfil ikke fundet på stien: {full_path}")
        st.info(f"Tjek at filen findes, og at din 'config'-mappe er i projektets rod: {PROJECT_ROOT}")
        return None  # Returner None for at signalere en fejl

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        st.error(f"Fejl ved indlæsning af JSON-fil {full_path}: {e}")
        return None

def load_value_config():
    """Indlæser konfigurationsfilen for Value Screener."""
    return load_config('strategies/value_screener_profiles.json')

def load_multibagger_config():
    """Indlæser konfigurationsfilen for Multibagger Screener."""
    return load_config('strategies/multibagger_profiles.json')

def load_region_mappings():
    """Indlæser region-mapping filen."""
    return load_config('mappings/region_mappings.json')