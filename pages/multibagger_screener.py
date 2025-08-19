import streamlit as st
import pandas as pd
from core.screening.multibagger_screener import screen_stocks
from config_loader import load_multibagger_config, load_region_mappings
import copy

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
    
    tooltip = ""
    if description:
        tooltip += f"**{description}**\n\n"
    
    if filter_type == 'scaled':
        min_val, max_val = filter_details.get('min_value', 0), filter_details.get('max_value', '∞')
        target_min, target_max = filter_details.get('target_min', 0), filter_details.get('target_max', 0)
        tooltip += f"**Type:** Lineær skalering\n"
        tooltip += f"- Værdiinterval: `{min_val}` til `{max_val}`\n"
        tooltip += f"- Giver mellem **{target_min}** og **{target_max}** point"
        
    elif filter_type == 'range':
        ranges = filter_details.get('ranges', [])
        tooltip += f"**Type:** Interval-baseret\n\n**Point-tildeling:**\n"
        sorted_ranges = sorted(ranges, key=lambda r: r.get('points', 0), reverse=True)
        
        for r in sorted_ranges:
            min_r, max_r = r.get('min'), r.get('max')
            points = r.get('points', 0)
            
            if min_r is not None and max_r is not None: 
                range_str = f"Mellem `{min_r}` og `{max_r}`"
            elif min_r is not None: 
                range_str = f"Over `{min_r}`"
            elif max_r is not None: 
                range_str = f"Under `{max_r}`"
            else: 
                continue
            
            tooltip += f"- {range_str}: **{points} point**\n"
            
    return tooltip.strip()

def initialize_undo_redo_state():
    if 'mb_weight_history' not in st.session_state:
        st.session_state['mb_weight_history'] = []
    if 'mb_current_history_index' not in st.session_state:
        st.session_state['mb_current_history_index'] = -1

def save_weights_to_history(weights, profile_name):
    weights_copy = copy.deepcopy(weights)
    
    last_weights = {}
    if (st.session_state['mb_weight_history'] and 
        st.session_state['mb_current_history_index'] >= 0):
        last_weights = st.session_state['mb_weight_history'][st.session_state['mb_current_history_index']]['weights']
    
    if not last_weights or weights_copy != last_weights:
        if st.session_state['mb_current_history_index'] < len(st.session_state['mb_weight_history']) - 1:
            st.session_state['mb_weight_history'] = st.session_state['mb_weight_history'][:st.session_state['mb_current_history_index'] + 1]
        
        history_entry = {
            'weights': weights_copy,
            'profile': profile_name,
            'timestamp': pd.Timestamp.now()
        }
        st.session_state['mb_weight_history'].append(history_entry)
        
        if len(st.session_state['mb_weight_history']) > 20:
            st.session_state['mb_weight_history'].pop(0)
        
        st.session_state['mb_current_history_index'] = len(st.session_state['mb_weight_history']) - 1

def undo_weights():
    if st.session_state['mb_current_history_index'] > 0:
        st.session_state['mb_current_history_index'] -= 1
        return st.session_state['mb_weight_history'][st.session_state['mb_current_history_index']]
    return None

def redo_weights():
    if st.session_state['mb_current_history_index'] < len(st.session_state['mb_weight_history']) - 1:
        st.session_state['mb_current_history_index'] += 1
        return st.session_state['mb_weight_history'][st.session_state['mb_current_history_index']]
    return None

# Load konfiguration
config_mb = load_multibagger_config()
region_mappings = load_region_mappings()

if not config_mb:
    st.error("Kunne ikke indlæse Multibagger-konfigurationsfil.")
    st.stop()

if 'processed_dataframe' not in st.session_state or st.session_state['processed_dataframe'] is None:
    st.warning("⚠️ Ingen data er indlæst. Gå til forsiden.")
    st.stop()

df_raw = st.session_state['processed_dataframe']
profile_names_mb = list(config_mb.keys())

initialize_undo_redo_state()

# Sidebar indstillinger
st.sidebar.title("⚙️ Indstillinger")

selected_profile_name_mb = st.sidebar.selectbox(
    "Vælg screeningsprofil", 
    profile_names_mb, 
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

advanced_mode_mb = st.sidebar.toggle(
    "Vis avancerede indstillinger", 
    key=f"advanced_toggle_mb_{selected_profile_name_mb}"
)

profile_mb = config_mb[selected_profile_name_mb]
profile_filters_mb = profile_mb.get('filters', {})
dynamic_weights_mb = {}

if advanced_mode_mb:
    st.sidebar.subheader("Juster Vægte")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("↶ Fortryd", key="mb_undo_btn", use_container_width=True):
            entry = undo_weights()
            if entry and entry['profile'] == selected_profile_name_mb:
                for name, weight in entry['weights'].items():
                    st.session_state[f"slider_mb_{selected_profile_name_mb}_{name}"] = int(weight)
                st.rerun()
    
    with col2:
        if st.button("↷ Gendan", key="mb_redo_btn", use_container_width=True):
            entry = redo_weights()
            if entry and entry['profile'] == selected_profile_name_mb:
                for name, weight in entry['weights'].items():
                    st.session_state[f"slider_mb_{selected_profile_name_mb}_{name}"] = int(weight)
                st.rerun()
    
    idx, total = st.session_state['mb_current_history_index'], len(st.session_state['mb_weight_history'])
    if total > 0: 
        st.sidebar.caption(f"Historie: {idx + 1}/{total}")

# Håndter vægte
for filter_name, filter_details in profile_filters_mb.items():
    default_weight = calculate_default_weight_mb(filter_details)
    
    if advanced_mode_mb and 'data_key' in filter_details:
        tooltip = get_tooltip_text(filter_details)
        dynamic_weights_mb[filter_name] = st.sidebar.slider(
            label=filter_details['data_key'],
            min_value=0,
            max_value=50,
            value=int(st.session_state.get(f"slider_mb_{selected_profile_name_mb}_{filter_name}", default_weight)),
            key=f"slider_mb_{selected_profile_name_mb}_{filter_name}",
            help=tooltip
        )
    else:
        dynamic_weights_mb[filter_name] = default_weight

if advanced_mode_mb:
    save_weights_to_history(dynamic_weights_mb, selected_profile_name_mb)

# Hovedindhold
st.info(f"**Beskrivelse:** {profile_mb.get('description', 'Ingen beskrivelse.')}")

with st.spinner("Kører screening..."):
    df_results = screen_stocks(
        df_raw, 
        selected_profile_name_mb, 
        config_mb, 
        selected_regions_mb, 
        dynamic_weights_mb
    )

st.header(f"Resultater for '{selected_profile_name_mb}'")
st.write(f"**{len(df_results)} aktier fundet**")

if not df_results.empty:
    score_column_name = next((col for col in df_results.columns if 'score' in col.lower()), 'Score')
    param_cols = [d['data_key'] for d in profile_filters_mb.values() if 'data_key' in d]
    
    display_cols = BASE_COLUMNS_TO_DISPLAY.copy()
    if score_column_name: 
        display_cols.insert(5, score_column_name)
    display_cols.extend(param_cols)
    
    seen = set()
    ordered_unique_cols = [x for x in display_cols if not (x in seen or seen.add(x))]
    final_cols = [col for col in ordered_unique_cols if col in df_results.columns]
    df_display = df_results[final_cols].copy()

    # Formatér tal-kolonner
    formatting_rules = {
        'Score_Percent': lambda x: f"{x:.1f}%" if pd.notnull(x) else "-",
        'Price': lambda x: f"${x:,.2f}" if pd.notnull(x) else "-",
        'Market Cap': lambda x: f"${x/1e9:.1f}B" if pd.notnull(x) and x >= 1e9 else f"${x/1e6:.0f}M" if pd.notnull(x) else "-",
        'PEG': lambda x: f"{x:.2f}" if pd.notnull(x) else "-",
        'Return on Invested Capital': lambda x: f"{x:.1%}" if pd.notnull(x) else "-",
        'Total Debt/Equity': lambda x: f"{x:.2f}" if pd.notnull(x) else "-",
        'P/Free Cash Flow': lambda x: f"{x:.1f}" if pd.notnull(x) else "-",
        'Operating Margin': lambda x: f"{x:.1%}" if pd.notnull(x) else "-",
        'Insider Ownership': lambda x: f"{x:.1%}" if pd.notnull(x) else "-",
        'Sales Growth Quarter Over Quarter': lambda x: f"{x:.1%}" if pd.notnull(x) else "-",
        'EPS Growth Next 5 Years': lambda x: f"{x:.1%}" if pd.notnull(x) else "-",
        'P/S': lambda x: f"{x:.1f}" if pd.notnull(x) else "-",
        'Performance (Quarter)': lambda x: f"{x:.1%}" if pd.notnull(x) else "-",
        'Relative Volume': lambda x: f"{x:.1f}" if pd.notnull(x) else "-",
        'Relative Strength Index (14)': lambda x: f"{x:.0f}" if pd.notnull(x) else "-",
        'EPS Growth Past 3 Years': lambda x: f"{x:.1%}" if pd.notnull(x) else "-"
    }
    
    # Anvend formatering
    for col, formatter in formatting_rules.items():
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(formatter)

    # Opret HTML-links
    df_display['Ticker'] = df_display['Ticker'].apply(
        lambda ticker: f'<a href="https://www.google.com/finance/quote/{ticker}" target="_blank">{ticker}</a>'
    )
    
    # Vis tabel med styling
    st.markdown(
        df_display.to_html(escape=False, index=False, classes='styled-table'),
        unsafe_allow_html=True
    )
    

    
    csv_full = df_results.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download fulde resultater som CSV", 
        csv_full, 
        f'multibagger_results_{selected_profile_name_mb}.csv', 
        'text/csv'
    )

    if advanced_mode_mb:
        with st.expander("📊 Aktive Vægte"):
            for name, weight in dynamic_weights_mb.items():
                details = profile_filters_mb.get(name, {})
                data_key = details.get('data_key', name)
                default = calculate_default_weight_mb(details)
                if weight != default:
                    st.write(f"**{data_key}:** {weight} point *(standard: {default})*")
                else:
                    st.write(f"**{data_key}:** {weight} point")
else:
    st.info("Ingen aktier matchede de valgte kriterier.")