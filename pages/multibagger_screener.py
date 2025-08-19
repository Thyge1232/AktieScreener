import streamlit as st
import pandas as pd
from core.screening.multibagger_screener import screen_stocks
from config_loader import load_multibagger_config, load_region_mappings

# --- Konfiguration ---
config_mb = load_multibagger_config()
region_mappings = load_region_mappings()
profile_names_mb = list(config_mb.get('profiles', {}).keys())
region_names_mb = list(region_mappings.keys())
PROFILES_MB = config_mb.get('profiles', {})

# --- Hoved-UI ---
st.title("📈 Multibagger Investment Screener")

# --- Sidepanel ---
st.sidebar.title("⚙️ Indstillinger")
advanced_mode_mb = st.sidebar.toggle("Vis avancerede indstillinger", value=False, key="multibagger_advanced_toggle")

# --- Hovedlogik ---
# 1. Tjek først om data er indlæst fra app.py
if 'processed_dataframe' in st.session_state and st.session_state['processed_dataframe'] is not None:
    df_raw = st.session_state['processed_dataframe']

    # --- UI-kontroller (vises kun når data er klar) ---
    selected_profile_name_mb = st.selectbox(
    "Vælg screeningsprofil", 
    profile_names_mb, 
    index=0, 
    key="multibagger_profile_select" # <-- TILFØJ DENNE LINJE
    )
    default_regions_mb = [r for r in ["North America", "EU & UK"] if r in region_names_mb]
    selected_regions_mb = st.multiselect(
        "Vælg region(er)", options=region_names_mb, default=default_regions_mb
    )

    # 2. Tjek derefter om en profil rent faktisk er valgt
    if selected_profile_name_mb:
        # --- Dynamisk Vægt Initialisering ---
        profile_filters = PROFILES_MB[selected_profile_name_mb]['filters']
        temp_weights = {}
        for filter_name, filter_details in profile_filters.items():
            if filter_details['type'] == 'range':
                temp_weights[filter_name] = max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=0)
            else:  # scaled
                temp_weights[filter_name] = max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))

        dynamic_weights_mb = {}
        if advanced_mode_mb:
            st.sidebar.subheader("Juster Vægte")
            st.sidebar.info(PROFILES_MB[selected_profile_name_mb]['description'])
            for filter_name, filter_details in profile_filters.items():
                data_key = filter_details['data_key']
                default_weight = temp_weights.get(filter_name, 0)
                dynamic_weights_mb[filter_name] = st.sidebar.slider(
                    label=data_key, min_value=0, max_value=50, value=int(default_weight),
                    key=f"{selected_profile_name_mb}_{filter_name}"
                )
        else:
            dynamic_weights_mb = temp_weights
            
        # --- Kør screening og vis resultater ---
        with st.spinner("Kører screening..."):
            df_results = screen_stocks(df_raw, selected_profile_name_mb, config_mb, selected_regions_mb, dynamic_weights_mb)
            st.header(f"Resultater for profil: {selected_profile_name_mb}")
            st.write(f"**Antal aktier fundet: {len(df_results)}**")

            if not df_results.empty:
                # Indsæt din visningslogik her
                st.dataframe(df_results, use_container_width=True)
            else:
                st.info("Ingen aktier opfyldte kriterierne for den valgte profil og filtre.")