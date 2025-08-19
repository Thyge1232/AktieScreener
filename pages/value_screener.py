import streamlit as st
import pandas as pd
from core.screening.value_screener import screen_stocks_value
from config_loader import load_value_config, load_region_mappings

# --- Konfiguration ---
config = load_value_config()
region_mappings = load_region_mappings()
profile_names = list(config.get('profiles', {}).keys())
region_names = list(region_mappings.keys())
PROFILES = config.get('profiles', {})

# --- Hoved-UI ---
st.title("📊 Value Investment Screener")

# --- Sidepanel ---
st.sidebar.title("⚙️ Indstillinger")
advanced_mode = st.sidebar.toggle("Vis avancerede indstillinger", value=False, key="value_advanced_toggle")

# --- Hovedlogik ---
# 1. Tjek først om data er indlæst fra app.py
if 'processed_dataframe' in st.session_state and st.session_state['processed_dataframe'] is not None:
    df_raw = st.session_state['processed_dataframe']

    # --- UI-kontroller (vises kun når data er klar) ---
    selected_profile_name = st.selectbox(
    "Vælg screeningsprofil", 
    profile_names, 
    index=0, 
    key="value_profile_select"  # <-- TILFØJ DENNE LINJE
    )
    default_regions = [r for r in ["North America", "EU & UK"] if r in region_names]
    selected_regions = st.multiselect(
        "Vælg region(er)", options=region_names, default=default_regions
    )

    # 2. Tjek derefter om en profil rent faktisk er valgt (den vil altid være det pga. index=0)
    if selected_profile_name:
        # --- Dynamisk Vægt Initialisering ---
        profile_filters = PROFILES[selected_profile_name]['filters']
        temp_weights = {}
        for filter_name, filter_details in profile_filters.items():
            filter_type = filter_details['type']
            if filter_type == 'range':
                default_weight = max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=0)
            elif filter_type == 'scaled':
                default_weight = max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))
            elif filter_type == 'hybrid_range_scaled':
                default_weight = max((r.get('base_points', 0) for r in filter_details.get('ranges', [])), default=0)
            else:
                default_weight = 0
            temp_weights[filter_name] = default_weight
        
        dynamic_weights = {}
        if advanced_mode:
            st.sidebar.subheader("Juster Vægte")
            st.sidebar.info(PROFILES[selected_profile_name]['description'])
            for filter_name, filter_details in profile_filters.items():
                data_key = filter_details['data_key']
                default_weight = temp_weights.get(filter_name, 0)
                dynamic_weights[filter_name] = st.sidebar.slider(
                    label=data_key, min_value=0, max_value=50, value=int(default_weight),
                    key=f"{selected_profile_name}_{filter_name}_advanced"
                )
        else:
            dynamic_weights = temp_weights

        # --- Kør screening og vis resultater ---
        with st.spinner("Kører screening..."):
            df_results = screen_stocks_value(df_raw, selected_profile_name, config, selected_regions, dynamic_weights)
            st.header(f"Resultater for profil: {selected_profile_name}")
            st.write(f"**Antal aktier fundet: {len(df_results)}**")

            if not df_results.empty:
                # Indsæt din visningslogik her (simpel/avanceret dataframe)
                st.dataframe(df_results, use_container_width=True)
            else:
                st.info("Ingen aktier opfyldte kriterierne for den valgte profil og filtre.")