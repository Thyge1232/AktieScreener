# config_loader.py
import json
import streamlit as st # Tilføj denne import øverst
import os

@st.cache_resource
def load_config(config_path=None):
    """Indlæser MULTIBAGGER profil-konfigurationsfilen."""
    if config_path is None:
        project_root = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(project_root, "config", "strategies", "multibagger_profiles.json")
    
    print(f"[DEBUG] Leder efter Multibagger profil-konfigurationsfil på sti: {config_path}")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Multibagger profil-konfigurationsfil ikke fundet: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if 'profiles' not in config and isinstance(config, dict):
        return {'profiles': config}
    return config

# ========================================================================
# == NY FUNKTION TILFØJES HER ==

@st.cache_resource
def load_value_config(config_path=None):
    """Indlæser VALUE SCREENER profil-konfigurationsfilen."""
    if config_path is None:
        project_root = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(project_root, "config", "strategies", "value_screener_profiles.json")
    
    print(f"[DEBUG] Leder efter Value profil-konfigurationsfil på sti: {config_path}")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Value profil-konfigurationsfil ikke fundet: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Sørger for at strukturen altid har et 'profiles' nøgleord i toppen
    if 'profiles' not in config and isinstance(config, dict):
        return {'profiles': config}
    return config
# ========================================================================


@st.cache_resource
def load_region_mappings(mappings_path=None):
    """Indlæser region-mapping filen."""
    if mappings_path is None:
        project_root = os.path.dirname(os.path.abspath(__file__))
        mappings_path = os.path.join(project_root, "config", "mappings", "region_mappings.json")

    print(f"[DEBUG] Leder efter region-mapping fil på sti: {mappings_path}")
    if not os.path.exists(mappings_path):
        raise FileNotFoundError(f"Region-mapping fil ikke fundet: {mappings_path}")

    with open(mappings_path, 'r', encoding='utf-8') as f:
        mappings = json.load(f)
    return mappings