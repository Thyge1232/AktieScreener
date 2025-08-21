# pages/multibagger_screener.py

import streamlit as st
import pandas as pd
import numpy as np
import copy
from core.screening.multibagger_screener import screen_stocks_multibagger
from config_loader import load_multibagger_config, load_region_mappings
from core.favorites_manager import load_favorites, save_favorites
from st_aggrid import GridOptionsBuilder

# Importer centrale hjælpefunktioner
from utils.aggrid_helpers import (
    JS_FAVORITE_CELL_RENDERER, JS_TICKER_LINK_RENDERER, JS_MARKET_CAP_FORMATTER, 
    JS_PRICE_FORMATTER, JS_SCORE_FORMATTER, JS_PERCENTAGE_FORMATTER, 
    JS_TWO_DECIMAL_FORMATTER, JS_FAVORITE_ROW_STYLE
)
from utils.validation import validate_screening_data, safe_aggrid_display

# --- SESSION STATE & LOKALE HJÆLPEFUNKTIONER ---
if 'force_rerender_count' not in st.session_state: st.session_state.force_rerender_count = 0
if 'mb_weight_history' not in st.session_state: st.session_state['mb_weight_history'] = []
if 'mb_current_history_index' not in st.session_state: st.session_state['mb_current_history_index'] = -1
if 'force_favorites_update' not in st.session_state: st.session_state.force_favorites_update = False
if st.session_state.force_favorites_update:
    st.session_state.force_rerender_count += 1
    st.session_state.force_favorites_update = False
    st.session_state.favorites = load_favorites()
    st.rerun()

st.title("🚀 Multibagger Investment Screener")

def calculate_default_weight_mb(filter_details):
    if 'weight' in filter_details: return filter_details['weight']
    filter_type = filter_details.get('type')
    if filter_type == 'scaled': return max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))
    if filter_type == 'range': return max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=0)
    return 0

def get_tooltip_text(filter_details):
    description = filter_details.get('description', ''); filter_type = filter_details.get('type', '')
    tooltip_parts = [f"**{description}**"] if description else []
    technical_parts = []
    if filter_type == 'scaled':
        min_val, max_val = filter_details.get('min_value', 0), filter_details.get('max_value', '∞')
        target_min, target_max = filter_details.get('target_min', 0), filter_details.get('target_max', 0)
        technical_parts.extend([f"**Type:** Lineær skalering", f"- Værdiinterval: `{min_val}` til `{max_val}`", f"- Giver **{target_min}** til **{target_max}** point"])
    elif filter_type == 'range':
        ranges = sorted(filter_details.get('ranges', []), key=lambda r: r.get('points', 0), reverse=True)
        technical_parts.append("**Type:** Interval-baseret")
        if ranges:
            technical_parts.append("\n**Point-tildeling:**")
            for r in ranges:
                min_r, max_r, points = r.get('min'), r.get('max'), r.get('points', 0)
                range_str = f"Mellem `{min_r}`-`{max_r}`" if min_r is not None and max_r is not None else f"Over `{min_r}`" if min_r is not None else f"Under `{max_r}`" if max_r is not None else ""
                if range_str: technical_parts.append(f"- {range_str}: **{points} point**")
    if technical_parts:
        if tooltip_parts: tooltip_parts.append("\n---\n")
        tooltip_parts.extend(technical_parts)
    return "\n".join(tooltip_parts)

def initialize_undo_redo_state():
    if 'mb_weight_history' not in st.session_state: st.session_state['mb_weight_history'] = []
    if 'mb_current_history_index' not in st.session_state: st.session_state['mb_current_history_index'] = -1

def save_weights_to_history(weights, profile_name):
    weights_copy = copy.deepcopy(weights); last_weights = {}
    if st.session_state['mb_weight_history'] and st.session_state['mb_current_history_index'] >= 0: last_weights = st.session_state['mb_weight_history'][st.session_state['mb_current_history_index']]['weights']
    if not last_weights or weights_copy != last_weights:
        if st.session_state['mb_current_history_index'] < len(st.session_state['mb_weight_history']) - 1: st.session_state['mb_weight_history'] = st.session_state['mb_weight_history'][:st.session_state['mb_current_history_index'] + 1]
        history_entry = {'weights': weights_copy, 'profile': profile_name, 'timestamp': pd.Timestamp.now()}
        st.session_state['mb_weight_history'].append(history_entry)
        if len(st.session_state['mb_weight_history']) > 20: st.session_state['mb_weight_history'].pop(0)
        st.session_state['mb_current_history_index'] = len(st.session_state['mb_weight_history']) - 1

def undo_weights():
    if st.session_state['mb_current_history_index'] > 0: st.session_state['mb_current_history_index'] -= 1; return st.session_state['mb_weight_history'][st.session_state['mb_current_history_index']]
    return None

def redo_weights():
    if st.session_state['mb_current_history_index'] < len(st.session_state['mb_weight_history']) - 1: st.session_state['mb_current_history_index'] += 1; return st.session_state['mb_weight_history'][st.session_state['mb_current_history_index']]
    return None

def add_results_summary(df_results):
    if not df_results.empty:
        st.markdown("---")
        st.subheader("📊 Resultat Sammendrag")
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Gns. Score", f"{df_results['Score_Percent'].mean():.1f}%")
        with col2: st.metric("Højeste Score", f"{df_results['Score_Percent'].max():.1f}%")
        with col3: st.metric("Unikke Sektorer", df_results['Sector'].nunique())
        with col4: st.metric("Unikke Lande", df_results['Country'].nunique())
        if 'Sector' in df_results.columns:
            sector_counts = df_results['Sector'].value_counts().head(5)
            with st.expander("🏭 Top 5 Sektorer i Resultaterne"):
                st.dataframe(sector_counts)

def add_filtering_controls(df_results, profile_config, profile_name):
    st.markdown("---")
    st.subheader("🎛️ Filtrer Resultater")
    
    score_key = f"filter_score_{profile_name}"
    sector_key = f"filter_sector_{profile_name}"
    market_cap_key = f"filter_market_cap_{profile_name}"

    if score_key not in st.session_state: st.session_state[score_key] = float(profile_config.get('min_score', 70))
    if sector_key not in st.session_state: st.session_state[sector_key] = []
    if market_cap_key not in st.session_state: st.session_state[market_cap_key] = "Alle"

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        st.slider("Minimum Score %", 0.0, 100.0, 5.0, key=score_key)
    with filter_col2:
        sektor_options = sorted(df_results['Sector'].unique()) if 'Sector' in df_results.columns else []
        st.multiselect("Vælg Sektorer:", options=sektor_options, key=sector_key)
    with filter_col3:
        st.select_slider("Markedsstørrelse:", options=["Alle", "Micro (<$300M)", "Small ($300M-$2B)", "Mid ($2B-$10B)", "Large (>$10B)"], key=market_cap_key)
    
    return st.session_state[score_key], st.session_state[sector_key], st.session_state[market_cap_key]

def apply_result_filters(df, min_score, sectors, market_cap):
    if df.empty: return df
    filtered_df = df.copy()
    if 'Score_Percent' in filtered_df.columns: filtered_df = filtered_df[filtered_df['Score_Percent'] >= min_score]
    if sectors and 'Sector' in filtered_df.columns: filtered_df = filtered_df[filtered_df['Sector'].isin(sectors)]
    if market_cap != "Alle" and 'Market Cap' in filtered_df.columns:
        cap_map = {"Micro (<$300M)": (0, 300_000_000), "Small ($300M-$2B)": (300_000_000, 2_000_000_000), "Mid ($2B-$10B)": (2_000_000_000, 10_000_000_000), "Large (>$10B)": (10_000_000_000, float('inf'))}
        min_cap, max_cap = cap_map.get(market_cap)
        filtered_df = filtered_df[filtered_df['Market Cap'].between(min_cap, max_cap)]
    return filtered_df

# --- DATA INDLÆSNING & SIDEBAR ---
config_mb, region_mappings = load_multibagger_config(), load_region_mappings()
if not config_mb: st.error("Kunne ikke indlæse Multibagger-konfigurationsfil."); st.stop()
if 'processed_dataframe' not in st.session_state or st.session_state['processed_dataframe'] is None: st.warning("⚠️ Ingen data er indlæst. Gå til forsiden."); st.stop()
df_raw = st.session_state['processed_dataframe']
profile_names_mb = list(config_mb.keys())
initialize_undo_redo_state()
st.sidebar.title("⚙️ Indstillinger")
selected_profile_name_mb = st.sidebar.selectbox("Vælg screeningsprofil", profile_names_mb, key="multibagger_profile_select")

region_names_mb = list(region_mappings.keys())
default_regions_mb = [r for r in ["North America", "EU & UK"] if r in region_names_mb]
region_select_key = "multibagger_region_select"
if region_select_key not in st.session_state:
    st.session_state[region_select_key] = default_regions_mb
selected_regions_mb = st.sidebar.multiselect("Vælg region(er)", options=region_names_mb, default=st.session_state[region_select_key], key=region_select_key)

advanced_mode_mb = st.sidebar.toggle("Vis avancerede indstillinger", key=f"advanced_toggle_mb_{selected_profile_name_mb}")
profile_mb = config_mb[selected_profile_name_mb]
dynamic_weights_mb = {}
if advanced_mode_mb:
    st.sidebar.subheader("Juster Vægte")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("↶ Fortryd", key="mb_undo_btn", use_container_width=True):
            entry = undo_weights();
            if entry and entry['profile'] == selected_profile_name_mb:
                for name, weight in entry['weights'].items(): st.session_state[f"slider_mb_{selected_profile_name_mb}_{name}"] = int(weight)
                st.rerun()
    with col2:
        if st.button("↷ Gendan", key="mb_redo_btn", use_container_width=True):
            entry = redo_weights();
            if entry and entry['profile'] == selected_profile_name_mb:
                for name, weight in entry['weights'].items(): st.session_state[f"slider_mb_{selected_profile_name_mb}_{name}"] = int(weight)
                st.rerun()
    idx, total = st.session_state['mb_current_history_index'], len(st.session_state['mb_weight_history'])
    if total > 0: st.sidebar.caption(f"Historie: {idx + 1}/{total}")
for filter_name, filter_details in profile_mb.get('filters', {}).items():
    default_weight = calculate_default_weight_mb(filter_details)
    if advanced_mode_mb and 'data_key' in filter_details:
        tooltip = get_tooltip_text(filter_details)
        dynamic_weights_mb[filter_name] = st.sidebar.slider(label=filter_details['data_key'], min_value=0, max_value=50, value=int(st.session_state.get(f"slider_mb_{selected_profile_name_mb}_{filter_name}", default_weight)), key=f"slider_mb_{selected_profile_name_mb}_{filter_name}", help=tooltip)
    else: dynamic_weights_mb[filter_name] = default_weight
if advanced_mode_mb: save_weights_to_history(dynamic_weights_mb, selected_profile_name_mb)

st.sidebar.markdown("---")
st.sidebar.subheader("⚡ Hurtige Handlinger")
if st.sidebar.button("🔄 Nulstil Vægte", help="Nulstiller alle justerede vægte for denne profil til standard.", use_container_width=True):
    for filter_name in profile_mb.get('filters', {}).keys():
        key = f"slider_mb_{selected_profile_name_mb}_{filter_name}"
        if key in st.session_state: del st.session_state[key]
    st.toast("Vægte nulstillet!", icon="🔄")
    st.rerun()

# --- HOVEDINDHOLD & SCREENING WORKFLOW ---
st.info(f"**Beskrivelse:** {profile_mb.get('description', 'Ingen beskrivelse.')}")

validation_errors, warnings = validate_screening_data(df_raw, profile_mb)
if validation_errors:
    st.error("❌ Kritiske datafejl forhindrer screening:")
    for error in validation_errors: st.markdown(f"&nbsp;&nbsp;&nbsp;• {error}")
    st.warning("Gå tilbage til Finviz, tilføj de manglende kolonner til din visning, og eksporter CSV-filen igen.")
    st.stop()
if warnings:
    with st.expander("⚠️ Advarsler om datakvalitet (klik for at se)"):
        for warning in warnings: st.warning(f"• {warning}")

with st.spinner("Kører screening..."):
    df_results = screen_stocks_multibagger(df_raw, selected_profile_name_mb, config_mb, selected_regions_mb, dynamic_weights_mb)

st.header(f"Resultater for '{selected_profile_name_mb}'")
add_results_summary(df_results)
min_score_filter, sector_filter, market_cap_filter = add_filtering_controls(df_results, profile_mb, selected_profile_name_mb)
df_filtered = apply_result_filters(df_results, min_score_filter, sector_filter, market_cap_filter)

st.write(f"**Viser {len(df_filtered)} af {len(df_results)} aktier, der matcher dine filtre.**")

if not df_filtered.empty:
    BASE_COLUMNS_TO_DISPLAY = ['Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Price', 'Market Cap']
    score_column_name = next((col for col in df_filtered.columns if 'score_percent' in col.lower()), 'Score_Percent')
    param_cols = [d['data_key'] for d in profile_mb.get('filters', {}).values() if 'data_key' in d]
    display_cols = BASE_COLUMNS_TO_DISPLAY.copy()
    if score_column_name in df_filtered.columns: display_cols.insert(display_cols.index('Price'), score_column_name)
    display_cols.extend(param_cols)
    seen = set(); ordered_unique_cols = [x for x in display_cols if not (x in seen or seen.add(x))]
    final_cols = [col for col in ordered_unique_cols if col in df_filtered.columns]
    df_for_grid = df_filtered[final_cols].copy()
    current_favorites = load_favorites()
    st.session_state.favorites = current_favorites
    df_for_grid['is_favorite'] = df_for_grid['Ticker'].isin(set(current_favorites))

    gb = GridOptionsBuilder.from_dataframe(df_for_grid)
    gb.configure_column("is_favorite", headerName="⭐", cellRenderer=JS_FAVORITE_CELL_RENDERER, width=60, editable=False, lockPosition=True)
    gb.configure_column("Ticker", cellRenderer=JS_TICKER_LINK_RENDERER)
    gb.configure_column("Market Cap", valueFormatter=JS_MARKET_CAP_FORMATTER)
    gb.configure_column("Price", valueFormatter=JS_PRICE_FORMATTER)
    if score_column_name in df_for_grid.columns: gb.configure_column(score_column_name, valueFormatter=JS_SCORE_FORMATTER)
    percent_cols = ['Return on Invested Capital', 'Operating Margin', 'Insider Ownership', 'Sales Growth Quarter Over Quarter', 'EPS Growth Next 5 Years', 'Performance (Quarter)', 'EPS Growth Past 3 Years']
    two_decimal_cols = ['PEG', 'Total Debt/Equity', 'P/Free Cash Flow', 'P/S', 'Relative Volume', 'Relative Strength Index (14)']
    for col in percent_cols:
        if col in df_for_grid.columns: gb.configure_column(col, valueFormatter=JS_PERCENTAGE_FORMATTER)
    for col in two_decimal_cols:
        if col in df_for_grid.columns: gb.configure_column(col, valueFormatter=JS_TWO_DECIMAL_FORMATTER)
    gb.configure_grid_options(rowStyle=JS_FAVORITE_ROW_STYLE)
    
    grid_options = gb.build()
    grid_key = f"aggrid_mb_{selected_profile_name_mb}_{st.session_state.force_rerender_count}"
    grid_response = safe_aggrid_display(df_for_grid, grid_options, grid_key)

    if grid_response and grid_response.get('data') is not None:
        updated_df = grid_response['data']
        tickers_in_view = set(df_for_grid['Ticker'])
        favorites_outside_view = set(st.session_state.favorites) - tickers_in_view
        favorites_in_view_after_change = set(updated_df[updated_df['is_favorite'] == True]['Ticker'])
        new_total_favorites_set = favorites_in_view_after_change.union(favorites_outside_view)
        if set(st.session_state.favorites) != new_total_favorites_set:
            st.session_state.favorites = sorted(list(new_total_favorites_set))
            save_favorites(st.session_state.favorites)
            st.toast("⭐ Favoritliste opdateret!", icon="✅")
            st.session_state.force_favorites_update = True
            st.session_state.force_rerender_count += 1
            st.rerun()

    st.markdown("---")
    csv_full = df_results.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download fulde resultater som CSV", csv_full, f'multibagger_results_{selected_profile_name_mb}.csv', 'text/csv')
    if advanced_mode_mb:
        with st.expander("📊 Aktive Vægte"):
            for name, weight in dynamic_weights_mb.items():
                details = profile_mb.get('filters', {}).get(name, {})
                data_key = details.get('data_key', name)
                default = calculate_default_weight_mb(details)
                st.write(f"**{data_key}:** {weight} point" + (f" *(standard: {default})*" if weight != default else ""))
else:
    st.info("Ingen aktier matchede de valgte kriterier eller filtre.")