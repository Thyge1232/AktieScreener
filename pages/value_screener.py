# pages/value_screener.py
import streamlit as st
import pandas as pd
from core.screening.value_screener import screen_stocks_value
from config_loader import load_value_config, load_region_mappings
import copy

# --- KONFIGURATION OG KONSTANTER ---
BASE_COLUMNS_TO_DISPLAY = ['Ticker', 'Company', 'Sector', 'Industry', 'Country', 'Price', 'Market Cap']
st.title("📊 Value Investment Screener")

# --- HJÆLPEFUNKTIONER ---

def format_market_cap(num):
    """Formaterer et stort tal til en læsbar streng med M, B, T for millioner, milliarder, billioner."""
    if pd.isna(num) or not isinstance(num, (int, float)): return "N/A"
    num = float(num)
    if num < 1_000_000_000: return f"${num / 1_000_000:.1f}M"
    if num < 1_000_000_000_000: return f"${num / 1_000_000_000:.2f}B"
    return f"${num / 1_000_000_000_000:.2f}T"

def calculate_default_weight_vs(filter_details):
    """Beregner standardvægten for et givent filter (inkl. hybrid-typen)."""
    filter_type = filter_details.get('type')
    if 'weight' in filter_details: return filter_details['weight']
    if 'points' in filter_details: return filter_details.get('points', 0)
    if filter_type == 'scaled': return max(filter_details.get('target_min', 0), filter_details.get('target_max', 0))
    if filter_type == 'range': return max((r.get('points', 0) for r in filter_details.get('ranges', [])), default=0)
    if filter_type == 'hybrid_range_scaled': return max((r.get('base_points', 0) + r.get('scaled_points', 0) for r in filter_details.get('ranges', [])), default=0)
    return 0

def convert_score_to_readable_value(min_val, max_val, data_key):
    """Konverterer scorer til læsbare værdier baseret på data type."""
    
    # Mapping af data_key til forventet format og omregningsfaktorer
    field_mappings = {
        # Procent-felter (scorer ~0-100 → 0-10%)
        'Insider Transactions': {'type': 'percent', 'factor': 0.1},
        'Insider Ownership': {'type': 'percent', 'factor': 0.3},
        'Operating Margin': {'type': 'percent', 'factor': 0.2},
        'Return on Invested Capital': {'type': 'percent', 'factor': 0.15},
        'Sales Growth Quarter Over Quarter': {'type': 'percent', 'factor': 0.25},
        'EPS Growth Next 5 Years': {'type': 'percent', 'factor': 0.2},
        'Performance (Quarter)': {'type': 'percent', 'factor': 0.3},
        'EPS Growth Past 3 Years': {'type': 'percent', 'factor': 0.2},
        
        # Ratio-felter (scorer ÷ 10)
        'PEG': {'type': 'ratio', 'factor': 10},
        'Total Debt/Equity': {'type': 'ratio', 'factor': 100},
        'P/S': {'type': 'ratio', 'factor': 20},
        'P/Free Cash Flow': {'type': 'ratio', 'factor': 5},
        
        # Specialfelter
        'Relative Volume': {'type': 'ratio', 'factor': 50},
        'Relative Strength Index (14)': {'type': 'direct', 'factor': 1},
    }
    
    mapping = field_mappings.get(data_key, {'type': 'score', 'factor': 1})
    
    if mapping['type'] == 'percent':
        if min_val is not None and max_val is not None:
            min_pct = min_val * mapping['factor']
            max_pct = max_val * mapping['factor']
            return f"{data_key} ca. {min_pct:.1f}%-{max_pct:.1f}%"
        elif min_val is not None:
            min_pct = min_val * mapping['factor']
            return f"{data_key} over ca. {min_pct:.1f}%"
        elif max_val is not None:
            max_pct = max_val * mapping['factor']
            return f"{data_key} under ca. {max_pct:.1f}%"
    
    elif mapping['type'] == 'ratio':
        if min_val is not None and max_val is not None:
            min_ratio = min_val / mapping['factor']
            max_ratio = max_val / mapping['factor']
            return f"{data_key} mellem ca. {min_ratio:.1f}-{max_ratio:.1f}"
        elif min_val is not None:
            min_ratio = min_val / mapping['factor']
            return f"{data_key} over ca. {min_ratio:.1f}"
        elif max_val is not None:
            max_ratio = max_val / mapping['factor']
            return f"{data_key} under ca. {max_ratio:.1f}"
    
    elif mapping['type'] == 'direct':
        # For felter som RSI hvor scorer ≈ faktisk værdi
        if min_val is not None and max_val is not None:
            return f"{data_key} mellem {min_val}-{max_val}"
        elif min_val is not None:
            return f"{data_key} over {min_val}"
        elif max_val is not None:
            return f"{data_key} under {max_val}"
    
    # Fallback: vis som scorer med note
    if min_val is not None and max_val is not None:
        return f"Score mellem {min_val} og {max_val} *(estimeret værdi)*"
    elif min_val is not None:
        return f"Score over {min_val} *(estimeret værdi)*"
    elif max_val is not None:
        return f"Score under {max_val} *(estimeret værdi)*"
    
    return f"{data_key}"

def get_tooltip_text(filter_details):
    """Genererer tooltip med faktiske dataværdier i stedet for scorer."""
    
    # Del 1: Beskrivelse
    description_part = []
    description = filter_details.get('description')
    if description:
        description_part.append(f"**{description}**")

    # Del 2: Teknisk implementering med faktiske værdier
    technical_parts = []
    filter_type = filter_details.get('type', '')
    data_key = filter_details.get('data_key', 'Værdi')
    
    if filter_type == 'scaled':
        min_val, max_val = filter_details.get('min_value', 0), filter_details.get('max_value', '∞')
        target_min, target_max = filter_details.get('target_min', 0), filter_details.get('target_max', 0)
        technical_parts.append(f"**Type:** Lineær skalering")
        technical_parts.append(f"- {data_key}: `{min_val}` til `{max_val}`")
        technical_parts.append(f"- Giver mellem **{target_min}** og **{target_max}** point")
        
    elif filter_type == 'range':
        ranges = filter_details.get('ranges', [])
        technical_parts.append(f"**Type:** Interval-baseret")
        if ranges:
            technical_parts.append(f"\n**Point-tildeling:**")
            sorted_ranges = sorted(ranges, key=lambda r: r.get('points', 0), reverse=True)
            for r in sorted_ranges:
                min_r, max_r, points = r.get('min'), r.get('max'), r.get('points', 0)
                
                # Konverter scorer til forståelige værdier
                range_str = convert_score_to_readable_value(min_r, max_r, data_key)
                technical_parts.append(f"- {range_str}: **{points} point**")
            
    elif filter_type == 'hybrid_range_scaled':
        ranges = filter_details.get('ranges', [])
        technical_parts.append(f"**Type:** Hybrid (Basis + Skaleret)")
        if ranges:
            technical_parts.append(f"\n**Point-tildeling:**")
            sorted_ranges = sorted(ranges, key=lambda r: r.get('base_points', 0) + r.get('scaled_points', 0), reverse=True)
            for r in sorted_ranges:
                min_r, max_r = r.get('min'), r.get('max')
                base, scaled = r.get('base_points', 0), r.get('scaled_points', 0)
                
                range_str = convert_score_to_readable_value(min_r, max_r, data_key)
                technical_parts.append(f"- {range_str}: **{base}** basispoint + op til **{scaled}** ekstra")

    # Sammensæt tooltip
    final_tooltip_parts = []
    if description_part:
        final_tooltip_parts.extend(description_part)
    
    if technical_parts:
        if final_tooltip_parts:
            final_tooltip_parts.append("\n---\n")
        final_tooltip_parts.extend(technical_parts)
        
    return "\n".join(final_tooltip_parts)

def initialize_undo_redo_state():
    """Initialiserer undo/redo state for Value Screener, hvis den ikke eksisterer."""
    if 'vs_weight_history' not in st.session_state:
        st.session_state['vs_weight_history'] = []
    if 'vs_current_history_index' not in st.session_state:
        st.session_state['vs_current_history_index'] = -1

def save_weights_to_history(weights, profile_name):
    """Gemmer nuværende vægte til historie KUN hvis de er ændret fra senest gemte tilstand."""
    weights_copy = copy.deepcopy(weights)
    
    last_weights = {}
    if (st.session_state['vs_weight_history'] and 
        st.session_state['vs_current_history_index'] >= 0):
        last_weights = st.session_state['vs_weight_history'][st.session_state['vs_current_history_index']]['weights']
    
    if not last_weights or weights_copy != last_weights:
        if st.session_state['vs_current_history_index'] < len(st.session_state['vs_weight_history']) - 1:
            st.session_state['vs_weight_history'] = st.session_state['vs_weight_history'][:st.session_state['vs_current_history_index'] + 1]
        
        history_entry = {
            'weights': weights_copy,
            'profile': profile_name,
            'timestamp': pd.Timestamp.now()
        }
        st.session_state['vs_weight_history'].append(history_entry)
        
        if len(st.session_state['vs_weight_history']) > 20:
            st.session_state['vs_weight_history'].pop(0)
        
        st.session_state['vs_current_history_index'] = len(st.session_state['vs_weight_history']) - 1

def undo_weights():
    """Fortryd til forrige vægte."""
    if st.session_state['vs_current_history_index'] > 0:
        st.session_state['vs_current_history_index'] -= 1
        return st.session_state['vs_weight_history'][st.session_state['vs_current_history_index']]
    return None

def redo_weights():
    """Gendan næste vægte."""
    if st.session_state['vs_current_history_index'] < len(st.session_state['vs_weight_history']) - 1:
        st.session_state['vs_current_history_index'] += 1
        return st.session_state['vs_weight_history'][st.session_state['vs_current_history_index']]
    return None


# --- DATA INDLÆSNING ---
config_vs = load_value_config()
region_mappings = load_region_mappings()

if config_vs is None or region_mappings is None:
    st.error("Kunne ikke indlæse konfigurationsfiler.")
    st.stop()
if 'processed_dataframe' not in st.session_state or st.session_state['processed_dataframe'] is None:
    st.warning("⚠️ Ingen data er indlæst. Gå til forsiden.")
    st.stop()

df_raw = st.session_state['processed_dataframe']
profile_names_vs = list(config_vs.keys())

# --- STATE MANAGEMENT ---
initialize_undo_redo_state()

# --- SIDEBAR UI ---
st.sidebar.title("⚙️ Indstillinger")
selected_profile_name_vs = st.sidebar.selectbox("Vælg screeningsprofil", profile_names_vs, key="value_profile_select")

region_names_vs = list(region_mappings.keys())
default_regions_vs = [r for r in ["North America", "EU & UK"] if r in region_names_vs]
selected_regions_vs = st.sidebar.multiselect("Vælg region(er)", options=region_names_vs, default=default_regions_vs, key="value_region_select")

advanced_mode_vs = st.sidebar.toggle("Vis avancerede indstillinger", key=f"advanced_toggle_vs_{selected_profile_name_vs}")

profile_vs = config_vs[selected_profile_name_vs]
profile_filters_vs = profile_vs.get('filters', {})
dynamic_weights_vs = {}

if advanced_mode_vs:
    st.sidebar.subheader("Juster Vægte")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("↶ Fortryd", key="vs_undo_btn", use_container_width=True):
            entry = undo_weights()
            if entry and entry['profile'] == selected_profile_name_vs:
                for name, weight in entry['weights'].items():
                    st.session_state[f"slider_vs_{selected_profile_name_vs}_{name}"] = int(weight)
                st.rerun()
    with col2:
        if st.button("↷ Gendan", key="vs_redo_btn", use_container_width=True):
            entry = redo_weights()
            if entry and entry['profile'] == selected_profile_name_vs:
                for name, weight in entry['weights'].items():
                    st.session_state[f"slider_vs_{selected_profile_name_vs}_{name}"] = int(weight)
                st.rerun()

    idx, total = st.session_state['vs_current_history_index'], len(st.session_state['vs_weight_history'])
    if total > 0: st.sidebar.caption(f"Historie: {idx + 1}/{total}")

# Loop for sliders og vægt-håndtering
for filter_name, filter_details in profile_filters_vs.items():
    default_weight = calculate_default_weight_vs(filter_details)
    if advanced_mode_vs and 'data_key' in filter_details:
        tooltip = get_tooltip_text(filter_details)
        dynamic_weights_vs[filter_name] = st.sidebar.slider(
            label=filter_details['data_key'], min_value=0, max_value=50, 
            value=int(st.session_state.get(f"slider_vs_{selected_profile_name_vs}_{filter_name}", default_weight)),
            key=f"slider_vs_{selected_profile_name_vs}_{filter_name}",
            help=tooltip
        )
    else:
        dynamic_weights_vs[filter_name] = default_weight

if advanced_mode_vs:
    save_weights_to_history(dynamic_weights_vs, selected_profile_name_vs)

# --- HOVEDINDHOLD ---
st.info(f"**Beskrivelse:** {profile_vs.get('description', 'Ingen beskrivelse.')}")

with st.spinner("Kører screening..."):
    df_results = screen_stocks_value(
        df=df_raw, profile_name=selected_profile_name_vs, config=config_vs,
        selected_regions=selected_regions_vs, dynamic_weights=dynamic_weights_vs
    )
    st.header(f"Resultater for '{selected_profile_name_vs}'")
    st.write(f"**{len(df_results)} aktier fundet**")

    if not df_results.empty:
        score_column_name = next((col for col in df_results.columns if 'score' in col.lower()), 'Score')
        param_cols = [d['data_key'] for d in profile_filters_vs.values() if 'data_key' in d]
        
        display_cols = BASE_COLUMNS_TO_DISPLAY.copy()
        if score_column_name: display_cols.insert(5, score_column_name)
        display_cols.extend(param_cols)
        
        seen = set()
        ordered_unique_cols = [x for x in display_cols if not (x in seen or seen.add(x))]
        final_cols = [col for col in ordered_unique_cols if col in df_results.columns]
        df_display = df_results[final_cols].copy()

        # --- TALFORMATERING ---
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
            'Insider Transactions': lambda x: f"{x:.1%}" if pd.notnull(x) else "-",
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
            lambda ticker: f'<a href="https://finance.yahoo.com/quote/{ticker}" target="_blank">{ticker}</a>'
        )
        
        # Vis tabel med styling
        st.markdown(
            df_display.to_html(escape=False, index=False, classes='styled-table'),
            unsafe_allow_html=True
        )
        
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