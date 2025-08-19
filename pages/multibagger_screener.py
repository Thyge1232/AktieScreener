import streamlit as st
import pandas as pd
from core.screening.multibagger_screener import screen_stocks
from config_loader import load_multibagger_config, load_region_mappings

# Definer basis-kolonner, vi altid vil se.
BASE_COLUMNS_TO_DISPLAY = [
    'Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Price', 'Market Cap'
]

st.title("📈 Multibagger Investment Screener")

# --- NY, ROBUST HJÆLPEFUNKTION TIL VÆGTE ---
def calculate_default_weight_mb(filter_details):
    """
    Beregner den maksimale point-værdi (vægten) specifikt for Multibagger-profiler.
    Den prioriterer 'weight'-nøglen, hvis den findes.
    """
    # Mange multibagger-filtre har en eksplicit 'weight'-nøgle.
    if 'weight' in filter_details:
        return filter_details['weight']

    filter_type = filter_details.get('type')
    if filter_type == 'scaled':
        return max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))
    if filter_type == 'range':
        return max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=0)
    
    return 0

# --- RETTET: Indlæser profiler korrekt ---
config_mb = load_multibagger_config()
region_mappings = load_region_mappings()

if not config_mb:
    st.error("Kunne ikke indlæse Multibagger-konfigurationsfil.")
    st.stop()

# Profilerne er det øverste niveau i JSON'en, ikke under en 'profiles'-nøgle.
profile_names_mb = list(config_mb.keys())
PROFILES_MB = config_mb

# --- Sidepanel ---
st.sidebar.title("⚙️ Indstillinger")

# --- Hovedlogik ---
if 'processed_dataframe' not in st.session_state or st.session_state['processed_dataframe'] is None:
    st.warning("⚠️ Ingen data er indlæst. Gå venligst til forsiden og upload en CSV-fil.")
    st.stop()

df_raw = st.session_state['processed_dataframe']

# --- UI-kontroller (vises kun når data er klar) ---
selected_profile_name_mb = st.sidebar.selectbox(
    "Vælg screeningsprofil", 
    profile_names_mb, 
    index=0, 
    key="multibagger_profile_select"
)

region_names_mb = list(region_mappings.keys())
default_regions_mb = [r for r in ["North America", "EU & UK"] if r in region_names_mb]
selected_regions_mb = st.sidebar.multiselect(
    "Vælg region(er)", 
    options=region_names_mb, 
    default=default_regions_mb,
    key="multibagger_region_select"
)

advanced_mode_mb = st.sidebar.toggle("Vis avancerede indstillinger", value=False, key="multibagger_advanced_toggle")

# --- Hovedlogik ---
profile_mb = PROFILES_MB[selected_profile_name_mb]
st.info(f"**Beskrivelse:** {profile_mb.get('description', 'Ingen beskrivelse tilgængelig.')}")

dynamic_weights_mb = {}
profile_filters_mb = profile_mb.get('filters', {})

if advanced_mode_mb:
    st.sidebar.subheader("Juster Vægte")

for filter_name, filter_details in profile_filters_mb.items():
    default_weight = calculate_default_weight_mb(filter_details)
    
    if advanced_mode_mb and 'data_key' in filter_details:
        dynamic_weights_mb[filter_name] = st.sidebar.slider(
            label=filter_details['data_key'], 
            min_value=0, max_value=50, 
            value=int(default_weight),
            key=f"slider_mb_{selected_profile_name_mb}_{filter_name}"
        )
    else:
        dynamic_weights_mb[filter_name] = default_weight
        
# --- Kør screening og vis resultater ---
with st.spinner("Kører screening..."):
    df_results = screen_stocks(df_raw, selected_profile_name_mb, config_mb, selected_regions_mb, dynamic_weights_mb)
    st.header(f"Resultater for profil: {selected_profile_name_mb}")
    st.write(f"**Antal aktier fundet: {len(df_results)}**")

    if not df_results.empty:
        # --- NY, SMARTERE DYNAMISK KOLONNE-HÅNDTERING ---
        score_column_name = next((col for col in df_results.columns if 'score' in col.lower()), None)
        profile_param_columns = [details['data_key'] for details in profile_filters_mb.values() if 'data_key' in details]
        
        combined_columns = BASE_COLUMNS_TO_DISPLAY.copy()
        if score_column_name:
            combined_columns.append(score_column_name)
        combined_columns.extend(profile_param_columns)
        
        ordered_unique_columns = []
        for col in combined_columns:
            if col not in ordered_unique_columns:
                ordered_unique_columns.append(col)
        
        final_columns_to_display = [col for col in ordered_unique_columns if col in df_results.columns]
        df_display = df_results[final_columns_to_display]
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        csv_full_data = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download fulde resultater som CSV", data=csv_full_data,
            file_name=f'multibagger_results_{selected_profile_name_mb}.csv', mime='text/csv',
        )
    else:
        st.info("Ingen aktier opfyldte kriterierne for den valgte profil og filtre.")