import json
import os
import streamlit as st

# Definer den absolutte sti til config-mappen
# Dette gør koden mere robust, uanset hvorfra den køres.
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')

# --- Central Konfigurations-funktion ---
# Streamlit's cache sikrer, at filerne kun læses fra disken én gang.
@st.cache_data
def load_config(file_path):
    """Indlæser en JSON-konfigurationsfil fra en given sti."""
    if not os.path.exists(file_path):
        st.error(f"Konfigurationsfil ikke fundet på sti: {file_path}")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        st.error(f"Fejl under indlæsning af konfigurationsfil {os.path.basename(file_path)}: {e}")
        return {}

# --- Hjælper-funktioner for hver specifik konfigurationsfil ---

def load_value_config():
    """Indlæser konfigurationsfilen for Value Screener."""
    file_path = os.path.join(CONFIG_DIR, 'strategies', 'value_screener_profiles.json')
    print(f"[DEBUG] Leder efter Value profil-konfigurationsfil på sti: {file_path}")
    return load_config(file_path)

def load_multibagger_config():
    """Indlæser konfigurationsfilen for Multibagger Screener."""
    # Sørg for at filnavnet matcher din faktiske fil
    file_path = os.path.join(CONFIG_DIR, 'strategies', 'multibagger_profiles.json') 
    print(f"[DEBUG] Leder efter Multibagger profil-konfigurationsfil på sti: {file_path}")
    return load_config(file_path)

def load_region_mappings():
    """Indlæser region-mapping filen."""
    file_path = os.path.join(CONFIG_DIR, 'mappings', 'region_mappings.json')
    print(f"[DEBUG] Leder efter region-mapping fil på sti: {file_path}")
    return load_config(file_path)