# pages/favorites.py
import streamlit as st
import pandas as pd
from core.favorites_manager import load_favorites, save_favorites
from core.data.client import get_data_for_favorites
# --- BRUG af utils ---
from utils.validation import safe_aggrid_display # Importeret fra utils
from utils.aggrid_helpers import ( # Importeret fra utils
    JS_FAVORITE_CELL_RENDERER,
    JS_TICKER_LINK_RENDERER,
    JS_PERCENTAGE_FORMATTER,
    JS_TWO_DECIMAL_FORMATTER,
    JS_FAVORITE_ROW_STYLE
)
# --------------------

# Import værdiansættelse med fejlhåndtering
try:
    from core.valuation.valuation_engine import get_valuation_data
    VALUATION_AVAILABLE = True
except ImportError as e:
    st.error(f"Værdiansættelsesmodul kunne ikke importeres: {e}")
    VALUATION_AVAILABLE = False

st.set_page_config(layout="wide", page_title="Mine Favoritter")

def format_currency(value):
    """Formaterer store tal til læsbare valuta-strenge."""
    if pd.isnull(value):
        return "-"
    try:
        value = float(value)
        if value >= 1e9:
            return f"${value/1e9:.2f}B"
        elif value >= 1e6:
            return f"${value/1e6:.1f}M"
        else:
            return f"${value:,.0f}"
    except (ValueError, TypeError):
        return "-"

def format_price(value):
    """Formaterer pris til USD med to decimaler."""
    if pd.isnull(value):
        return "-"
    try:
        return f"${float(value):.2f}"
    except (ValueError, TypeError):
        return "-"

# --- SESSION STATE INITIALISERING ---
if 'force_rerender_count' not in st.session_state:
    st.session_state.force_rerender_count = 0

if 'force_favorites_update' not in st.session_state:
    st.session_state.force_favorites_update = False

# Håndter favorit-opdateringer fra andre sider
if st.session_state.force_favorites_update:
    st.session_state.force_rerender_count += 1
    st.session_state.force_favorites_update = False
    st.session_state.favorites = load_favorites()
    st.rerun()

st.title("⭐ Mine Favoritter")

# Synkroniser med global session state
if 'favorites' in st.session_state:
    favorite_tickers = st.session_state.favorites
else:
    favorite_tickers = load_favorites()
    st.session_state.favorites = favorite_tickers

if not favorite_tickers:
    st.info("Du har endnu ikke tilføjet nogen favoritter. Find aktier i en af screenerne og tilføj dem med ➕.")
    st.stop()

# Vis live data sektion
st.subheader("Live Data Opdatering")

# Data opdatering med loading state
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("🔄 Opdater Data", use_container_width=True):
        with st.spinner("Henter seneste data..."):
            try:
                live_data_df = get_data_for_favorites(favorite_tickers)
                if not live_data_df.empty:
                    st.session_state.favorites_data = live_data_df
                    st.success(f"✅ Data opdateret for {len(live_data_df)} aktier")
                else:
                    st.warning("⚠️ Ingen data kunne hentes. Tjek internetforbindelse.")
            except Exception as e:
                st.error(f"❌ Fejl ved datahentning: {str(e)}")

with col2:
    # Link til den detaljerede værdiansættelsesside
    if st.button("🔍 Detaljeret Værdiansættelse", use_container_width=True):
        # Kræver Streamlit 1.33+. For ældre versioner brug st.experimental_rerun() og navigation i app.py
        st.switch_page("pages/valuation.py") 

with col3:
    st.info("💡 Klik opdater-knappen for at få de seneste kurser")

# Vis data med AgGrid hvis tilgængelig
if 'favorites_data' in st.session_state and not st.session_state.favorites_data.empty:
    df_display = st.session_state.favorites_data.copy()
    
    # Formatter store tal FØRST for at undgå BigInt-problemer i JavaScript
    if 'Market Cap' in df_display.columns:
        df_display['Market Cap'] = df_display['Market Cap'].apply(format_currency)
    
    if 'Price' in df_display.columns:
        df_display['Price'] = df_display['Price'].apply(format_price)
    
    # Tilføj favorit-kolonne
    df_display['is_favorite'] = True
    
    # Reorganiser kolonner
    cols = ['is_favorite'] + [col for col in df_display.columns if col != 'is_favorite']
    df_display = df_display[cols]
    
    # --- AgGrid konfiguration ---
    from st_aggrid import GridOptionsBuilder # Importer her for klarhed
    gb = GridOptionsBuilder.from_dataframe(df_display)
    
    # Favorit-kolonne - BRUGER hjælperen
    gb.configure_column(
        "is_favorite", 
        headerName="⭐", 
        cellRenderer=JS_FAVORITE_CELL_RENDERER, # <--- BRUGT
        width=60, 
        editable=False, 
        lockPosition=True
    )
    
    # Ticker som klikbart link - BRUGER hjælperen
    if 'Ticker' in df_display.columns:
        gb.configure_column("Ticker", cellRenderer=JS_TICKER_LINK_RENDERER, width=80) # <--- BRUGT
    
    # Company navn med passende bredde
    if 'Company' in df_display.columns:
        gb.configure_column("Company", width=200)
    
    # Formatering for numeriske kolonner - BRUGER hjælpere
    percent_cols = ['Dividend Yield', 'Performance (Quarter)', 'Performance (Year)']
    decimal_cols = ['P/E', 'EPS', 'PEG', 'P/S']
    
    for col in percent_cols:
        if col in df_display.columns and df_display[col].dtype in ['float64', 'int64']:
            gb.configure_column(col, valueFormatter=JS_PERCENTAGE_FORMATTER, width=120) # <--- BRUGT
    
    for col in decimal_cols:
        if col in df_display.columns and df_display[col].dtype in ['float64', 'int64']:
            gb.configure_column(col, valueFormatter=JS_TWO_DECIMAL_FORMATTER, width=80) # <--- BRUGT
    
    # Row styling for favoritter - BRUGER hjælperen
    gb.configure_grid_options(getRowStyle=JS_FAVORITE_ROW_STYLE) # <--- BRUGT
    
    # Byg grid options
    grid_options = gb.build()
    grid_key = f"favorites_aggrid_{st.session_state.force_rerender_count}"
    
    # Vis tabellen med sikker funktion - BRUGER hjælperen
    grid_response = safe_aggrid_display(df_display, grid_options, grid_key) # <--- BRUGT
    
    # --- Håndter favorit-ændringer ---
    if grid_response and grid_response.get('data') is not None:
        updated_df = pd.DataFrame(grid_response['data'])
        
        # Find fjernede favoritter
        current_favorites = set(df_display['Ticker'])
        remaining_favorites = set(updated_df[updated_df['is_favorite'] == True]['Ticker'])
        removed_tickers = current_favorites - remaining_favorites
        
        if removed_tickers:
            # Opdater globale favoritter
            updated_favorites = [t for t in st.session_state.favorites if t not in removed_tickers]
            st.session_state.favorites = sorted(updated_favorites)
            save_favorites(st.session_state.favorites)
            
            # Fjern fra cached data
            if 'favorites_data' in st.session_state:
                st.session_state.favorites_data = st.session_state.favorites_data[
                    ~st.session_state.favorites_data['Ticker'].isin(removed_tickers)
                ]
            
            st.success(f"🗑️ Fjernede {', '.join(removed_tickers)} fra favoritter")
            st.rerun()

# Statistik sidebar hvis data findes
if 'favorites_data' in st.session_state and not st.session_state.favorites_data.empty:
    with st.sidebar:
        st.subheader("📊 Portfolio Oversigt")
        df = st.session_state.favorites_data
        
        st.metric("Antal aktier", len(df))
        
        # Beregn gennemsnit hvor muligt
        try:
            if 'P/E' in df.columns:
                avg_pe = df['P/E'].mean()
                if not pd.isna(avg_pe):
                    st.metric("Gennemsnit P/E", f"{avg_pe:.1f}")
            
            if 'Dividend Yield' in df.columns:
                avg_div = df['Dividend Yield'].mean()
                if not pd.isna(avg_div):
                    st.metric("Gennemsnit Dividend", f"{avg_div:.1f}%")
            
            # Sektor fordeling hvis tilgængelig
            if 'Sector' in df.columns:
                sector_counts = df['Sector'].value_counts()
                if not sector_counts.empty:
                    st.subheader("🏢 Sektorer")
                    for sector, count in sector_counts.head(5).items():
                        if pd.notna(sector):
                            st.write(f"• {sector}: {count}")
        
        except Exception as e:
            st.warning(f"Fejl ved beregning af portfolio statistik: {e}")
