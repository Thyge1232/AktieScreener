# Filnavn: pages/multibagger_screener.py

import streamlit as st
import pandas as pd
# OPDATERET IMPORT: Kalder den nye, normaliserede backend-funktion
from core.screening.multibagger_screener import screen_stocks_multibagger
from config_loader import load_multibagger_config, load_region_mappings
import copy
# NYE IMPORTS: Tilføjet for AgGrid og favoritter
from core.favorites_manager import load_favorites, save_favorites
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# --- KONFIGURATION OG HJÆLPEFUNKTIONER (stort set uændret) ---
BASE_COLUMNS_TO_DISPLAY = ['Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Price', 'Market Cap']
st.title("📈 Multibagger Investment Screener")

def calculate_default_weight_mb(filter_details):
    if 'weight' in filter_details: 
        return filter_details['weight']
    filter_type = filter_details.get('type')
    if filter_type == 'scaled': 
        return max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))
    if filter_type == 'range': 
        return max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=0)
    return 0

def get_tooltip_text(filter_details):
    description = filter_details.get('description', '')
    filter_type = filter_details.get('type', '')
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
                if range_str:
                    technical_parts.append(f"- {range_str}: **{points} point**")

    if technical_parts:
        if tooltip_parts: tooltip_parts.append("\n---\n")
        tooltip_parts.extend(technical_parts)
    return "\n".join(tooltip_parts)

# --- Undo/Redo og State Management (uændret, men vigtigt) ---
def initialize_undo_redo_state():
    if 'mb_weight_history' not in st.session_state: st.session_state['mb_weight_history'] = []
    if 'mb_current_history_index' not in st.session_state: st.session_state['mb_current_history_index'] = -1
def save_weights_to_history(weights, profile_name):
    weights_copy = copy.deepcopy(weights)
    last_weights = {}
    if st.session_state['mb_weight_history'] and st.session_state['mb_current_history_index'] >= 0:
        last_weights = st.session_state['mb_weight_history'][st.session_state['mb_current_history_index']]['weights']
    if not last_weights or weights_copy != last_weights:
        if st.session_state['mb_current_history_index'] < len(st.session_state['mb_weight_history']) - 1:
            st.session_state['mb_weight_history'] = st.session_state['mb_weight_history'][:st.session_state['mb_current_history_index'] + 1]
        history_entry = {'weights': weights_copy, 'profile': profile_name, 'timestamp': pd.Timestamp.now()}
        st.session_state['mb_weight_history'].append(history_entry)
        if len(st.session_state['mb_weight_history']) > 20: st.session_state['mb_weight_history'].pop(0)
        st.session_state['mb_current_history_index'] = len(st.session_state['mb_weight_history']) - 1
def undo_weights():
    if st.session_state['mb_current_history_index'] > 0:
        st.session_state['mb_current_history_index'] -= 1; return st.session_state['mb_weight_history'][st.session_state['mb_current_history_index']]
    return None
def redo_weights():
    if st.session_state['mb_current_history_index'] < len(st.session_state['mb_weight_history']) - 1:
        st.session_state['mb_current_history_index'] += 1; return st.session_state['mb_weight_history'][st.session_state['mb_current_history_index']]
    return None

# --- DATA INDLÆSNING & SIDEBAR (uændret) ---
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
selected_regions_mb = st.sidebar.multiselect("Vælg region(er)", options=region_names_mb, default=default_regions_mb, key="multibagger_region_select")
advanced_mode_mb = st.sidebar.toggle("Vis avancerede indstillinger", key=f"advanced_toggle_mb_{selected_profile_name_mb}")
profile_mb = config_mb[selected_profile_name_mb]
profile_filters_mb = profile_mb.get('filters', {})
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
for filter_name, filter_details in profile_filters_mb.items():
    default_weight = calculate_default_weight_mb(filter_details)
    if advanced_mode_mb and 'data_key' in filter_details:
        tooltip = get_tooltip_text(filter_details)
        dynamic_weights_mb[filter_name] = st.sidebar.slider(label=filter_details['data_key'], min_value=0, max_value=50, value=int(st.session_state.get(f"slider_mb_{selected_profile_name_mb}_{filter_name}", default_weight)), key=f"slider_mb_{selected_profile_name_mb}_{filter_name}", help=tooltip)
    else: dynamic_weights_mb[filter_name] = default_weight
if advanced_mode_mb: save_weights_to_history(dynamic_weights_mb, selected_profile_name_mb)

# --- HOVEDINDHOLD & SCREENING ---
st.info(f"**Beskrivelse:** {profile_mb.get('description', 'Ingen beskrivelse.')}")
with st.spinner("Kører screening..."):
    # OPDATERET: Kalder den nye backend-funktion
    df_results = screen_stocks_multibagger(df_raw, selected_profile_name_mb, config_mb, selected_regions_mb, dynamic_weights_mb)
st.header(f"Resultater for '{selected_profile_name_mb}'")
st.write(f"**{len(df_results)} aktier fundet**")

# --- NYT: AGGRID TABELVISNING (erstatter den gamle HTML-tabel) ---
if not df_results.empty:
    score_column_name = next((col for col in df_results.columns if 'score_percent' in col.lower()), 'Score_Percent')
    param_cols = [d['data_key'] for d in profile_filters_mb.values() if 'data_key' in d]
    display_cols = BASE_COLUMNS_TO_DISPLAY.copy()
    if score_column_name in df_results.columns: display_cols.insert(display_cols.index('Price'), score_column_name)
    display_cols.extend(param_cols)
    seen = set(); ordered_unique_cols = [x for x in display_cols if not (x in seen or seen.add(x))]
    final_cols = [col for col in ordered_unique_cols if col in df_results.columns]
    df_for_grid = df_results[final_cols].copy()

    if 'favorites' not in st.session_state: st.session_state.favorites = load_favorites()
    df_for_grid.insert(0, 'is_favorite', df_for_grid['Ticker'].isin(st.session_state.favorites))

    # Genanvendelige JsCode-definitioner fra value_screener
    js_button_renderer = JsCode("""class FavoriteCellRenderer{init(params){this.params=params;this.eGui=document.createElement("div");this.eGui.style.cssText="text-align: center; cursor: pointer; font-size: 1.2em;";this.updateIcon();this.eGui.addEventListener("click",this.onClick.bind(this))}onClick(){this.params.node.setDataValue("is_favorite",!this.params.value)}updateIcon(){this.eGui.innerHTML=this.params.value?"⭐":"➕"}getGui(){return this.eGui}refresh(params){this.params=params;this.updateIcon();return true}}""")
    js_ticker_renderer = JsCode("""class TickerLinkRenderer{init(params){this.eGui=document.createElement("a");this.eGui.innerText=params.value;this.eGui.href=`https://finviz.com/quote.ashx?t=${params.value}&ty=l&ta=0&p=w&r=y2`;this.eGui.target="_blank";this.eGui.style.cssText="color: #ADD8E6; text-decoration: underline;"}getGui(){return this.eGui}}""")
    js_market_cap_formatter = JsCode("function(params){if(params.value==null||isNaN(params.value))return'-';const num=parseFloat(params.value);if(num<1e9)return'$'+(num/1e6).toFixed(1)+'M';if(num<1e12)return'$'+(num/1e9).toFixed(2)+'B';return'$'+(num/1e12).toFixed(2)+'T'}")
    js_price_formatter = JsCode("function(params){return params.value!=null&&!isNaN(params.value)?'$'+parseFloat(params.value).toFixed(2):'-'}")
    js_score_formatter = JsCode("function(params){return params.value!=null&&!isNaN(params.value)?parseFloat(params.value).toFixed(1)+'%':'-'}")
    js_percentage_formatter = JsCode("function(params){return params.value!=null&&!isNaN(params.value)?(parseFloat(params.value)*100).toFixed(1)+'%':'-'}")
    js_two_decimal_formatter = JsCode("function(params){return params.value!=null&&!isNaN(params.value)?parseFloat(params.value).toFixed(2):'-'}")
    
    gb = GridOptionsBuilder.from_dataframe(df_for_grid)
    gb.configure_column("is_favorite", headerName="⭐", cellRenderer=js_button_renderer, width=60, editable=False, lockPosition=True)
    gb.configure_column("Ticker", cellRenderer=js_ticker_renderer)
    gb.configure_column("Market Cap", valueFormatter=js_market_cap_formatter)
    gb.configure_column("Price", valueFormatter=js_price_formatter)
    if score_column_name in df_for_grid.columns: gb.configure_column(score_column_name, valueFormatter=js_score_formatter)
    
    # Definer formatering for Multibagger-specifikke kolonner
    percent_cols = ['Return on Invested Capital', 'Operating Margin', 'Insider Ownership', 'Sales Growth Quarter Over Quarter', 'EPS Growth Next 5 Years', 'Performance (Quarter)', 'EPS Growth Past 3 Years']
    two_decimal_cols = ['PEG', 'Total Debt/Equity', 'P/Free Cash Flow', 'P/S', 'Relative Volume', 'Relative Strength Index (14)']
    
    for col in percent_cols:
        if col in df_for_grid.columns: gb.configure_column(col, valueFormatter=js_percentage_formatter)
    for col in two_decimal_cols:
        if col in df_for_grid.columns: gb.configure_column(col, valueFormatter=js_two_decimal_formatter)

    js_row_style = JsCode("function(params){if(params.data.is_favorite){return{'backgroundColor':'rgba(255, 255, 0, 0.1)'}}}")
    gb.configure_grid_options(rowStyle=js_row_style)
    
    grid_options = gb.build()
    grid_response = AgGrid(df_for_grid, gridOptions=grid_options, allow_unsafe_jscode=True, theme="streamlit-dark", fit_columns_on_grid_load=True, height=600, update_on=['cellValueChanged'])

    if grid_response and grid_response.get('data') is not None:
        updated_df = grid_response['data']
        original_favorites_set = set(st.session_state.favorites)
        new_favorites_set = set(updated_df[updated_df['is_favorite'] == True]['Ticker'])
        if original_favorites_set != new_favorites_set:
            st.session_state.favorites = list(new_favorites_set)
            save_favorites(st.session_state.favorites)
            st.rerun()

    st.markdown("---")
    csv_full = df_results.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download fulde resultater som CSV", csv_full, f'multibagger_results_{selected_profile_name_mb}.csv', 'text/csv')

    if advanced_mode_mb:
        with st.expander("📊 Aktive Vægte"):
            for name, weight in dynamic_weights_mb.items():
                details = profile_filters_mb.get(name, {})
                data_key = details.get('data_key', name)
                default = calculate_default_weight_mb(details)
                st.write(f"**{data_key}:** {weight} point" + (f" *(standard: {default})*" if weight != default else ""))
else:
    st.info("Ingen aktier matchede de valgte kriterier.")