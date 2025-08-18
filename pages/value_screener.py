import streamlit as st
import pandas as pd
from core.data.csv_processor import process_finviz_csv
from core.screening.multibagger_screener import screen_stocks
from config_loader import load_value_config, load_region_mappings

# --- Konfiguration (Kun én gang) ---
st.set_page_config(page_title="Value Screener", layout="wide")
config = load_value_config() 
region_mappings = load_region_mappings()
profile_names = list(config.get('profiles', {}).keys())
region_names = list(region_mappings.keys())
PROFILES = config.get('profiles', {})

# --- Sidepanel ---
st.sidebar.title("⚙️ Indstillinger")
advanced_mode = st.sidebar.toggle("Vis avancerede indstillinger", value=False)

# --- Hoved-UI ---
st.title("📊 Value Investment Screener")
st.markdown("Upload en Finviz CSV-fil og vælg en value-strategi.")
# Den overflødige 'config = ...' linje er fjernet herfra.

# Standard-kontroller
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Upload Finviz CSV-fil", type="csv")
with col2:
    selected_profile_name = st.selectbox("Vælg screeningsprofil", profile_names, index=0)

default_regions = [r for r in ["North America", "EU & UK"] if r in region_names]
selected_regions = st.multiselect(
    "Vælg region(er) (vælg ingen for at inkludere alle)",
    options=region_names,
    default=default_regions
)

# --- Avancerede kontroller (uændret) ---
dynamic_weights = {}
if advanced_mode and selected_profile_name:
    st.sidebar.subheader("Juster Vægte")
    st.sidebar.info(PROFILES[selected_profile_name]['description'])
    profile_filters = PROFILES[selected_profile_name]['filters']
    for filter_name, filter_details in profile_filters.items():
        data_key = filter_details['data_key']
        if filter_details['type'] == 'range':
            default_weight = max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=0)
        else:
            default_weight = max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))
        
        dynamic_weights[filter_name] = st.sidebar.slider(
            label=data_key, min_value=0, max_value=50, value=int(default_weight),
            key=f"{selected_profile_name}_{filter_name}"
        )
else:
    if selected_profile_name:
        profile_filters = PROFILES[selected_profile_name]['filters']
        for filter_name, filter_details in profile_filters.items():
             if filter_details['type'] == 'range':
                dynamic_weights[filter_name] = max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=0)
             else:
                dynamic_weights[filter_name] = max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))

# --- Logik (Rettet) ---
if uploaded_file is not None and selected_profile_name:
    with st.spinner("Behandler data..."):
        df_raw = process_finviz_csv(uploaded_file)
        
        if df_raw.empty:
            st.error("Kunne ikke indlæse eller parse CSV-filen.")
        else:
            # ========================================================================
            # == DET ENESTE KORREKTE KALD TIL screen_stocks ==
            df_results = screen_stocks(df_raw, selected_profile_name, config, selected_regions, dynamic_weights)
            # ========================================================================

            st.header(f"Resultater for profil: {selected_profile_name}")
            st.write(f"**Antal aktier fundet: {len(df_results)}**")

            # Resten af koden fortsætter herfra
            if not df_results.empty:
                if advanced_mode:
                    # ... (Avanceret visning er uændret)
                    for _, row in df_results.iterrows():
                        row_cols = st.columns((1, 3, 2, 3, 1, 2, 1, 1.5))
                        ticker_link = f"[{row['Ticker']}](https://finviz.com/quote.ashx?t={row['Ticker']})"
                        row_cols[0].markdown(ticker_link, unsafe_allow_html=True)
                        row_cols[1].write(row['Company'])
                        row_cols[2].write(row['Sector'])
                        row_cols[3].write(row['Industry'])
                        row_cols[4].write(row['Country'])
                        row_cols[5].write(f"{row['Market Cap']:,.0f}" if pd.notna(row['Market Cap']) else "N/A")
                        row_cols[6].write(f"{row['Price']:.2f}")
                        row_cols[7].markdown(f"**{row['Score_Percent']:.2f}**")
                        
                        with st.expander("Vis score-detaljer"):
                            breakdown_cols = st.columns(2)
                            col_idx = 0
                            for filter_name, filter_details in PROFILES[selected_profile_name]['filters'].items():
                                data_key = filter_details['data_key']
                                points = row.get(f"points_{filter_name}", 0)
                                max_points = dynamic_weights.get(filter_name, 0)
                                breakdown_cols[col_idx % 2].write(f"*{data_key}*: **{points:.2f}** / {max_points} point")
                                col_idx += 1
                        st.markdown("---")
                else:
                    # ... (Simpel visning er uændret)
                    df_display = df_results.copy()
                    display_columns = ['Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Market Cap', 'Price', 'Score_Percent']
                    profile_metrics = [details['data_key'] for details in PROFILES[selected_profile_name]['filters'].values()]
                    final_display_columns = display_columns[:6] + list(set(profile_metrics)) + display_columns[6:]
                    existing_columns = [col for col in final_display_columns if col in df_display.columns]
                    df_simple_view = df_display[existing_columns]
                    st.dataframe(df_simple_view, use_container_width=True, column_config={"Market Cap": st.column_config.NumberColumn(label="Market Cap ($)",format="%,.0f"), "Score_Percent": st.column_config.NumberColumn(label="Score (%)", format="%.2f")}, hide_index=True)

                csv_result = df_results.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download fulde resultater som CSV",
                    data=csv_result,
                    file_name=f'value_screener_results_{selected_profile_name}.csv',
                    mime='text/csv',
                )
            else:
                st.info("Ingen aktier opfyldte kriterierne for den valgte profil og filtre.")
else:
    st.info("Upload venligst en CSV-fil for at starte.")