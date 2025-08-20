# pages/value_screener.py
import streamlit as st
import pandas as pd
from core.screening.value_screener import screen_stocks_value
from config_loader import load_value_config, load_region_mappings
import copy
from core.favorites_manager import load_favorites, save_favorites
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# --- KONFIGURATION OG HJÆLPEFUNKTIONER (UÆNDRET) ---
BASE_COLUMNS_TO_DISPLAY = ['Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Price', 'Market Cap']
st.title("📊 Value Investment Screener")
# ... (alle dine uændrede hjælpefunktioner fra format_market_cap til redo_weights) ...
def format_market_cap(num):
    if pd.isna(num) or not isinstance(num, (int, float)): return "N/A"
    num = float(num);
    if num < 1_000_000_000: return f"${num / 1_000_000:.1f}M"
    if num < 1_000_000_000_000: return f"${num / 1_000_000_000:.2f}B"
    return f"${num / 1_000_000_000_000:.2f}T"
def calculate_default_weight_vs(filter_details):
    filter_type = filter_details.get('type');
    if 'weight' in filter_details: return filter_details['weight']
    if 'points' in filter_details: return filter_details.get('points', 0)
    if filter_type == 'scaled': return max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))
    if filter_type == 'range': return max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=0)
    if filter_type == 'hybrid_range_scaled': return max((r.get('base_points', 0) + r.get('scaled_points', 0) for r in filter_details.get('ranges', [])), default=0)
    return 0
def convert_score_to_readable_value(min_val, max_val, data_key):
    field_mappings = {'Insider Transactions': {'type': 'percent', 'factor': 0.1},'Insider Ownership': {'type': 'percent', 'factor': 0.3},'Operating Margin': {'type': 'percent', 'factor': 0.2},'Return on Invested Capital': {'type': 'percent', 'factor': 0.15},'Sales Growth Quarter Over Quarter': {'type': 'percent', 'factor': 0.25},'EPS Growth Next 5 Years': {'type': 'percent', 'factor': 0.2},'Performance (Quarter)': {'type': 'percent', 'factor': 0.3},'EPS Growth Past 3 Years': {'type': 'percent', 'factor': 0.2},'PEG': {'type': 'ratio', 'factor': 10},'Total Debt/Equity': {'type': 'ratio', 'factor': 100},'P/S': {'type': 'ratio', 'factor': 20},'P/Free Cash Flow': {'type': 'ratio', 'factor': 5},'Relative Volume': {'type': 'ratio', 'factor': 50},'Relative Strength Index (14)': {'type': 'direct', 'factor': 1},}
    mapping = field_mappings.get(data_key, {'type': 'score', 'factor': 1})
    if mapping['type'] == 'percent':
        if min_val is not None and max_val is not None: return f"{data_key} ca. {min_val * mapping['factor']:.1f}%-{max_val * mapping['factor']:.1f}%"
        elif min_val is not None: return f"{data_key} over ca. {min_val * mapping['factor']:.1f}%"
        elif max_val is not None: return f"{data_key} under ca. {max_val * mapping['factor']:.1f}%"
    elif mapping['type'] == 'ratio':
        if min_val is not None and max_val is not None: return f"{data_key} mellem ca. {min_val / mapping['factor']:.1f}-{max_val / mapping['factor']:.1f}"
        elif min_val is not None: return f"{data_key} over ca. {min_val / mapping['factor']:.1f}"
        elif max_val is not None: return f"{data_key} under ca. {max_val / mapping['factor']:.1f}"
    elif mapping['type'] == 'direct':
        if min_val is not None and max_val is not None: return f"{data_key} mellem {min_val}-{max_val}"
        elif min_val is not None: return f"{data_key} over {min_val}"
        elif max_val is not None: return f"{data_key} under {max_val}"
    if min_val is not None and max_val is not None: return f"Score mellem {min_val} og {max_val} *(estimeret værdi)*"
    elif min_val is not None: return f"Score over {min_val} *(estimeret værdi)*"
    elif max_val is not None: return f"Score under {max_val} *(estimeret værdi)*"
    return data_key
def get_tooltip_text(filter_details):
    description_part = [f"**{d}**" for d in [filter_details.get('description')] if d]
    technical_parts, filter_type, data_key = [], filter_details.get('type', ''), filter_details.get('data_key', 'Værdi')
    if filter_type == 'scaled':
        min_v, max_v, t_min, t_max = filter_details.get('min_value', 0), filter_details.get('max_value', '∞'), filter_details.get('target_min', 0), filter_details.get('target_max', 0)
        technical_parts.extend([f"**Type:** Lineær skalering", f"- {data_key}: `{min_v}` til `{max_v}`", f"- Giver mellem **{t_min}** og **{t_max}** point"])
    elif filter_type == 'range':
        ranges = sorted(filter_details.get('ranges', []), key=lambda r: r.get('points', 0), reverse=True)
        technical_parts.append(f"**Type:** Interval-baseret")
        if ranges: technical_parts.extend([f"\n**Point-tildeling:**"] + [f"- {convert_score_to_readable_value(r.get('min'), r.get('max'), data_key)}: **{r.get('points', 0)} point**" for r in ranges])
    elif filter_type == 'hybrid_range_scaled':
        ranges = sorted(filter_details.get('ranges', []), key=lambda r: r.get('base_points', 0) + r.get('scaled_points', 0), reverse=True)
        technical_parts.append(f"**Type:** Hybrid (Basis + Skaleret)")
        if ranges: technical_parts.extend([f"\n**Point-tildeling:**"] + [f"- {convert_score_to_readable_value(r.get('min'), r.get('max'), data_key)}: **{r.get('base_points', 0)}** basispoint + op til **{r.get('scaled_points', 0)}** ekstra" for r in ranges])
    final_tooltip_parts = description_part
    if technical_parts:
        if final_tooltip_parts: final_tooltip_parts.append("\n---\n")
        final_tooltip_parts.extend(technical_parts)
    return "\n".join(final_tooltip_parts)
def initialize_undo_redo_state():
    if 'vs_weight_history' not in st.session_state: st.session_state['vs_weight_history'] = []
    if 'vs_current_history_index' not in st.session_state: st.session_state['vs_current_history_index'] = -1
def save_weights_to_history(weights, profile_name):
    weights_copy = copy.deepcopy(weights)
    last_weights = {}
    if st.session_state['vs_weight_history'] and st.session_state['vs_current_history_index'] >= 0:
        last_weights = st.session_state['vs_weight_history'][st.session_state['vs_current_history_index']]['weights']
    if not last_weights or weights_copy != last_weights:
        if st.session_state['vs_current_history_index'] < len(st.session_state['vs_weight_history']) - 1:
            st.session_state['vs_weight_history'] = st.session_state['vs_weight_history'][:st.session_state['vs_current_history_index'] + 1]
        history_entry = {'weights': weights_copy, 'profile': profile_name, 'timestamp': pd.Timestamp.now()}
        st.session_state['vs_weight_history'].append(history_entry)
        if len(st.session_state['vs_weight_history']) > 20: st.session_state['vs_weight_history'].pop(0)
        st.session_state['vs_current_history_index'] = len(st.session_state['vs_weight_history']) - 1
def undo_weights():
    if st.session_state['vs_current_history_index'] > 0:
        st.session_state['vs_current_history_index'] -= 1; return st.session_state['vs_weight_history'][st.session_state['vs_current_history_index']]
    return None
def redo_weights():
    if st.session_state['vs_current_history_index'] < len(st.session_state['vs_weight_history']) - 1:
        st.session_state['vs_current_history_index'] += 1; return st.session_state['vs_weight_history'][st.session_state['vs_current_history_index']]
    return None

# --- DATA INDLÆSNING & SIDEBAR (UÆNDRET) ---
config_vs, region_mappings = load_value_config(), load_region_mappings()
if config_vs is None or region_mappings is None: st.error("Kunne ikke indlæse konfigurationsfiler."); st.stop()
if 'processed_dataframe' not in st.session_state or st.session_state['processed_dataframe'] is None: st.warning("⚠️ Ingen data er indlæst. Gå til forsiden."); st.stop()
df_raw = st.session_state['processed_dataframe']
profile_names_vs = list(config_vs.keys())
initialize_undo_redo_state()
st.sidebar.title("⚙️ Indstillinger")
selected_profile_name_vs = st.sidebar.selectbox("Vælg screeningsprofil", profile_names_vs, key="value_profile_select")
region_names_vs = list(region_mappings.keys())
default_regions_vs = [r for r in ["North America", "EU & UK"] if r in region_names_vs]
selected_regions_vs = st.sidebar.multiselect("Vælg region(er)", options=region_names_vs, default=default_regions_vs, key="value_region_select")
advanced_mode_vs = st.sidebar.toggle("Vis avancerede indstillinger", key=f"advanced_toggle_vs_{selected_profile_name_vs}")
profile_vs, profile_filters_vs, dynamic_weights_vs = config_vs[selected_profile_name_vs], config_vs[selected_profile_name_vs].get('filters', {}), {}
if advanced_mode_vs:
    st.sidebar.subheader("Juster Vægte")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("↶ Fortryd", key="vs_undo_btn", use_container_width=True):
            entry = undo_weights();
            if entry and entry['profile'] == selected_profile_name_vs:
                for name, weight in entry['weights'].items(): st.session_state[f"slider_vs_{selected_profile_name_vs}_{name}"] = int(weight)
                st.rerun()
    with col2:
        if st.button("↷ Gendan", key="vs_redo_btn", use_container_width=True):
            entry = redo_weights();
            if entry and entry['profile'] == selected_profile_name_vs:
                for name, weight in entry['weights'].items(): st.session_state[f"slider_vs_{selected_profile_name_vs}_{name}"] = int(weight)
                st.rerun()
    idx, total = st.session_state['vs_current_history_index'], len(st.session_state['vs_weight_history'])
    if total > 0: st.sidebar.caption(f"Historie: {idx + 1}/{total}")
for filter_name, filter_details in profile_filters_vs.items():
    default_weight = calculate_default_weight_vs(filter_details)
    if advanced_mode_vs and 'data_key' in filter_details:
        tooltip = get_tooltip_text(filter_details)
        dynamic_weights_vs[filter_name] = st.sidebar.slider(label=filter_details['data_key'], min_value=0, max_value=50, value=int(st.session_state.get(f"slider_vs_{selected_profile_name_vs}_{filter_name}", default_weight)), key=f"slider_vs_{selected_profile_name_vs}_{filter_name}", help=tooltip)
    else: dynamic_weights_vs[filter_name] = default_weight
if advanced_mode_vs: save_weights_to_history(dynamic_weights_vs, selected_profile_name_vs)

# --- HOVEDINDHOLD & SCREENING (UÆNDRET) ---
st.info(f"**Beskrivelse:** {profile_vs.get('description', 'Ingen beskrivelse.')}")
with st.spinner("Kører screening..."):
    df_results = screen_stocks_value(df=df_raw, profile_name=selected_profile_name_vs, config=config_vs, selected_regions=selected_regions_vs, dynamic_weights=dynamic_weights_vs)
    st.header(f"Resultater for '{selected_profile_name_vs}'")
    st.write(f"**{len(df_results)} aktier fundet**")

    # --- TABELVISNING (SEKTION MED RETTELSER) ---
    if not df_results.empty:
        # 1. Forbered den RÅ DataFrame til AgGrid
        score_column_name = next((col for col in df_results.columns if 'score' in col.lower()), 'Score')
        param_cols = [d['data_key'] for d in profile_filters_vs.values() if 'data_key' in d]
        display_cols = BASE_COLUMNS_TO_DISPLAY.copy()
        if score_column_name in df_results.columns:
            try: insert_index = display_cols.index('Price')
            except ValueError: insert_index = len(display_cols)
            display_cols.insert(insert_index, score_column_name)
        display_cols.extend(param_cols)
        seen = set(); ordered_unique_cols = [x for x in display_cols if not (x in seen or seen.add(x))]
        final_cols = [col for col in ordered_unique_cols if col in df_results.columns]
        df_for_grid = df_results[final_cols].copy()

        # 2. Tilføj en boolean favorit-kolonne
        if 'favorites' not in st.session_state: st.session_state.favorites = load_favorites()
        df_for_grid.insert(0, 'is_favorite', df_for_grid['Ticker'].isin(st.session_state.favorites))

        # 3. Definer GENANVENDELIGE JsCode formatters og renderers
        # --- Cell Renderers (for knapper og links)
        js_button_renderer = JsCode("""
        class FavoriteCellRenderer {
            init(params) {
                this.params = params; this.eGui = document.createElement('div');
                this.eGui.style.cssText = 'text-align: center; cursor: pointer; font-size: 1.2em;';
                this.updateIcon();
                this.eGui.addEventListener('click', this.onClick.bind(this));
            }
            onClick() { this.params.node.setDataValue('is_favorite', !this.params.value); }
            updateIcon() { this.eGui.innerHTML = this.params.value ? "⭐" : "➕"; }
            getGui() { return this.eGui; }
            refresh(params) { this.params = params; this.updateIcon(); return true; }
        }""")

        js_ticker_renderer = JsCode("""
        class TickerLinkRenderer {
            init(params) {
                this.eGui = document.createElement('a'); this.eGui.innerText = params.value;
                this.eGui.href = `https://finviz.com/quote.ashx?t=${params.value}&ta=0&p=w&ty=l&r=y2`;
                this.eGui.target = '_blank';
                this.eGui.style.cssText = 'color: #ADD8E6; text-decoration: underline;';
            }
            getGui() { return this.eGui; }
        }""")
        
        # --- Value Formatters (for tal, procenter, valuta etc.)
        js_market_cap_formatter = JsCode("function(params) { if(params.value == null || isNaN(params.value)) return '-'; const num = parseFloat(params.value); if(num < 1e9) return '$' + (num / 1e6).toFixed(1) + 'M'; if(num < 1e12) return '$' + (num / 1e9).toFixed(2) + 'B'; return '$' + (num / 1e12).toFixed(2) + 'T'; }")
        js_price_formatter = JsCode("function(params) { return params.value != null && !isNaN(params.value) ? '$' + parseFloat(params.value).toFixed(2) : '-' }")
        js_score_formatter = JsCode("function(params) { return params.value != null && !isNaN(params.value) ? parseFloat(params.value).toFixed(1) + '%' : '-' }")
        js_percentage_formatter = JsCode("function(params) { return params.value != null && !isNaN(params.value) ? (parseFloat(params.value) * 100).toFixed(1) + '%' : '-' }")
        js_two_decimal_formatter = JsCode("function(params) { return params.value != null && !isNaN(params.value) ? parseFloat(params.value).toFixed(2) : '-' }")

        # 4. Byg Grid Options
        gb = GridOptionsBuilder.from_dataframe(df_for_grid)

        # 5. Konfigurer de specielle kolonner
        gb.configure_column("is_favorite", headerName="⭐", cellRenderer=js_button_renderer, width=60, editable=False, lockPosition=True)
        gb.configure_column("Ticker", cellRenderer=js_ticker_renderer)

        # 6. Anvend de genanvendelige formatters på de relevante kolonner
        gb.configure_column("Market Cap", valueFormatter=js_market_cap_formatter)
        gb.configure_column("Price", valueFormatter=js_price_formatter)
        if score_column_name in df_for_grid.columns:
             gb.configure_column(score_column_name, valueFormatter=js_score_formatter)
        
        # Lister over kolonner, der skal have samme formatering
        percent_cols = [
            'Return on Invested Capital', 'Operating Margin', 'Profit Margin', 
            'Insider Ownership', 'Insider Transactions', 
            'Sales Growth Quarter Over Quarter', 
            'EPS Growth Next 5 Years', 'EPS Growth Past 3 Years',
            'EPS Growth Past 5 Years',  # Variation med lille 'g'
            'EPS Growth',               # Kort, generisk version
            'Performance (Quarter)',
            'Performance (Year)',
            'EPS Growth This Year',
            'Dividend Yield']
        two_decimal_cols = ['P/E', 'PEG', 'Total Debt/Equity', 'P/S', 'P/Free Cash Flow', 'Relative Volume', 'Relative Strength Index (14)','Price vs. Book/sh','Payout Ratio']

        for col in percent_cols:
            if col in df_for_grid.columns:
                gb.configure_column(col, valueFormatter=js_percentage_formatter)
        for col in two_decimal_cols:
            if col in df_for_grid.columns:
                gb.configure_column(col, valueFormatter=js_two_decimal_formatter)

        # 7. Definer række-styling for favoritter
        js_row_style = JsCode("function(params) { if (params.data.is_favorite) { return { 'backgroundColor': 'rgba(255, 255, 0, 0.1)' }; } }")
        gb.configure_grid_options(rowStyle=js_row_style)

        # 8. Byg og vis tabellen
        grid_options = gb.build()
        grid_response = AgGrid(
            df_for_grid,
            gridOptions=grid_options,
            allow_unsafe_jscode=True,
            theme="streamlit-dark",
            fit_columns_on_grid_load=True,
            height=600,
            update_on=['cellValueChanged'], # Lyt efter ændringer på celleniveau
        )

        # 9. Håndter klik på ⭐-ikonet
        if grid_response and grid_response.get('data') is not None:
            updated_df = grid_response['data']
            original_favorites_set = set(st.session_state.favorites)
            new_favorites_set = set(updated_df[updated_df['is_favorite'] == True]['Ticker'])

            if original_favorites_set != new_favorites_set:
                st.session_state.favorites = list(new_favorites_set)
                save_favorites(st.session_state.favorites)
                st.rerun()

        # 10. UI elementer under tabellen (uændret)
        st.markdown("---")
        csv_full = df_results.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download fulde resultater som CSV", csv_full, f'value_results_{selected_profile_name_vs}.csv', 'text/csv')
        if advanced_mode_vs:
            with st.expander("📊 Aktive Vægte"):
                for name, weight in dynamic_weights_vs.items():
                    details = profile_filters_vs.get(name, {})
                    data_key = details.get('data_key', name)
                    default = calculate_default_weight_vs(details)
                    if weight != default:
                        st.write(f"**{data_key}:** {weight} point *(standard: {default})*")
                    else:
                        st.write(f"**{data_key}:** {weight} point")
    else:
        st.info("Ingen aktier matchede de valgte kriterier.")