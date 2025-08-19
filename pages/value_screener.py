# pages/value_screener.py
import streamlit as st
import pandas as pd
from core.screening.value_screener import screen_stocks_value
from config_loader import load_value_config, load_region_mappings

# Definer de grundlæggende kolonner, vi altid vil se, uanset profil.
BASE_COLUMNS_TO_DISPLAY = [
    'Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Price', 'Market Cap'
]

st.title("📊 Value Investment Screener")

# Funktion til at beregne default vægt (ingen ændringer her)
def calculate_default_weight(filter_details):
    filter_type = filter_details.get('type')
    if filter_type == 'scaled':
        return max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))
    if filter_type == 'range':
        return max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=0)
    if filter_type == 'hybrid_range_scaled':
        return max((r.get('base_points', 0) + r.get('scaled_points', 0) for r in filter_details.get('ranges', [])), default=0)
    if 'points' in filter_details:
        return filter_details.get('points', 0)
    return 0

# --- Indlæs konfiguration ---
config = load_value_config()
region_mappings = load_region_mappings()

if config is None or region_mappings is None:
    st.error("Kunne ikke indlæse konfigurationsfiler. Applikationen kan ikke fortsætte.")
    st.stop()

if 'processed_dataframe' not in st.session_state or st.session_state['processed_dataframe'] is None:
    st.warning("⚠️ Ingen data er indlæst. Gå venligst til forsiden og upload en CSV-fil.")
    st.stop()

df_raw = st.session_state['processed_dataframe']

# --- SIDEBAR UI ---
st.sidebar.title("⚙️ Indstillinger")
profile_names = list(config.keys())
selected_profile_name = st.sidebar.selectbox("Vælg screeningsprofil", profile_names)
region_names = list(region_mappings.keys())
default_regions = [r for r in ["North America", "EU & UK"] if r in region_names]
selected_regions = st.sidebar.multiselect("Vælg region(er)", options=region_names, default=default_regions)
advanced_mode = st.sidebar.toggle("Vis avancerede indstillinger", key=f"advanced_toggle_{selected_profile_name}")

# --- HOVEDLOGIK ---
profile = config[selected_profile_name]
st.info(f"**Beskrivelse:** {profile.get('description', 'Ingen beskrivelse tilgængelig.')}")

dynamic_weights = {}
profile_filters = profile.get('filters', {})
if advanced_mode:
    st.sidebar.subheader("Juster Vægte")
for filter_name, filter_details in profile_filters.items():
    default_weight = calculate_default_weight(filter_details)
    if advanced_mode and 'data_key' in filter_details:
        dynamic_weights[filter_name] = st.sidebar.slider(
            label=filter_details.get('data_key', filter_name), min_value=0, max_value=50, 
            value=int(default_weight), key=f"slider_{selected_profile_name}_{filter_name}"
        )
    else:
        dynamic_weights[filter_name] = default_weight

# --- Kør screening og vis resultater ---
with st.spinner("Kører screening..."):
    df_results = screen_stocks_value(
        df=df_raw, profile_name=selected_profile_name, config=config,
        selected_regions=selected_regions, dynamic_weights=dynamic_weights
    )
    st.header(f"Resultater for '{selected_profile_name}'")
    st.write(f"**{len(df_results)} aktier fundet**")

    if not df_results.empty:
        # --- NY, SMARTERE DYNAMISK KOLONNE-HÅNDTERING ---
        
        # 1. Find score-kolonnen (robust metode)
        score_column_name = next((col for col in df_results.columns if 'score' in col.lower()), None)

        # 2. Hent de specifikke parameter-kolonner for den VALGTE profil
        profile_param_columns = [details['data_key'] for details in profile_filters.values() if 'data_key' in details]
        
        # 3. Sammensæt den fulde liste: Først basis-info, så score, så de profil-specifikke parametre
        combined_columns = BASE_COLUMNS_TO_DISPLAY.copy()
        if score_column_name:
            combined_columns.append(score_column_name)
        combined_columns.extend(profile_param_columns)
        
        # 4. Fjern eventuelle dubletter, men bevar rækkefølgen
        ordered_unique_columns = []
        for col in combined_columns:
            if col not in ordered_unique_columns:
                ordered_unique_columns.append(col)
        
        # 5. Filtrer listen, så vi kun viser kolonner, der rent faktisk eksisterer i resultaterne
        final_columns_to_display = [col for col in ordered_unique_columns if col in df_results.columns]
        df_display = df_results[final_columns_to_display]
        
        # 6. Vis den rensede og nu hyper-relevante DataFrame
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Download-knappen giver stadig adgang til ALLE kolonner
        csv_full_data = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download fulde resultater som CSV", data=csv_full_data,
            file_name=f'full_results_{selected_profile_name}.csv', mime='text/csv',
        )
    else:
        st.info("Ingen aktier matchede de valgte kriterier.")