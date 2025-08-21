# pages/favorites.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.favorites_manager import load_favorites, save_favorites
from core.data.api_client import get_data_for_favorites, get_valuation_data
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from utils.validation import safe_aggrid_display
from utils.aggrid_helpers import (
    JS_FAVORITE_CELL_RENDERER,
    JS_TICKER_LINK_RENDERER,
    JS_PERCENTAGE_FORMATTER,
    JS_TWO_DECIMAL_FORMATTER,
    JS_FAVORITE_ROW_STYLE
)
from core.valuation.valuation_engine import (
    CompanyProfile, ValuationInputs, WACCInputs, 
    ComprehensiveValuation, ValuationMethodSelector
)

st.set_page_config(layout="wide")

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

def determine_company_type(data_row):
    """Afgør virksomhedstype baseret på finansielle karakteristika"""
    try:
        pe_ratio = float(data_row.get('P/E', 0))
        dividend_yield = float(data_row.get('Dividend Yield', 0))
        debt_equity = float(data_row.get('Debt to Equity', 0))
        
        # Logik baseret på strategien
        if pe_ratio > 25 and dividend_yield < 2:
            return 'startup'
        elif debt_equity > 3:  # Høj gearing tyder på bank/finansiel
            return 'bank'
        elif dividend_yield > 4:  # Høj dividend tyder på moden/utility
            return 'mature'
        else:
            return 'mature'
    except:
        return 'mature'

def create_valuation_inputs(ticker_data):
    """Konverterer API-data til ValuationInputs objekt"""
    try:
        return ValuationInputs(
            revenue=float(ticker_data.get('Revenue', 0)) * 1e6,  # Konverter til kr
            ebitda=float(ticker_data.get('EBITDA', 0)) * 1e6,
            net_income=float(ticker_data.get('Net Income', 0)) * 1e6,
            free_cash_flow=float(ticker_data.get('Operating Cash Flow', 0)) * 1e6 * 0.8,  # Estimat
            book_value=float(ticker_data.get('Book Value', 0)) * 1e6,
            dividend_per_share=float(ticker_data.get('Dividend Per Share', 0)),
            shares_outstanding=float(ticker_data.get('Shares Outstanding', 1)) * 1e6,
            revenue_growth_rate=float(ticker_data.get('Quarterly Revenue Growth', 0.05)),
            terminal_growth_rate=0.025,  # Standard antagelse
            beta=float(ticker_data.get('Beta', 1.0)),
            debt_to_equity=float(ticker_data.get('Debt to Equity', 0.3)),
            interest_coverage=float(ticker_data.get('Interest Coverage', 8))
        )
    except Exception as e:
        st.error(f"Fejl ved oprettelse af værdiansættelse inputs: {e}")
        return None

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
    if st.button("🎯 Hent Værdiansættelse", use_container_width=True):
        if 'favorites_data' in st.session_state and not st.session_state.favorites_data.empty:
            with st.spinner("Udfører værdiansættelse..."):
                try:
                    valuation_data = get_valuation_data(favorite_tickers[:3])  # Begræns til 3 for API-grænser
                    if not valuation_data.empty:
                        st.session_state.valuation_data = valuation_data
                        st.success(f"🎯 Værdiansættelse klar for {len(valuation_data)} aktier")
                    else:
                        st.warning("Ingen værdiansættelsesdata kunne hentes")
                except Exception as e:
                    st.error(f"Fejl ved værdiansættelse: {e}")
        else:
            st.warning("Opdater først grunddata")

with col3:
    # Vis sidste opdateringstidspunkt hvis data findes
    if 'favorites_data' in st.session_state:
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
    gb = GridOptionsBuilder.from_dataframe(df_display)
    
    # Favorit-kolonne
    gb.configure_column(
        "is_favorite", 
        headerName="⭐", 
        cellRenderer=JS_FAVORITE_CELL_RENDERER,
        width=60, 
        editable=False, 
        lockPosition=True
    )
    
    # Ticker som klikbart link
    if 'Ticker' in df_display.columns:
        gb.configure_column("Ticker", cellRenderer=JS_TICKER_LINK_RENDERER, width=80)
    
    # Company navn med passende bredde
    if 'Company' in df_display.columns:
        gb.configure_column("Company", width=200)
    
    # Formatering for numeriske kolonner (kun hvis de ikke er pre-formaterede strenge)
    percent_cols = ['Dividend Yield', 'Performance (Quarter)', 'Performance (Year)']
    decimal_cols = ['P/E', 'EPS', 'PEG', 'P/S']
    
    for col in percent_cols:
        if col in df_display.columns and df_display[col].dtype in ['float64', 'int64']:
            gb.configure_column(col, valueFormatter=JS_PERCENTAGE_FORMATTER, width=120)
    
    for col in decimal_cols:
        if col in df_display.columns and df_display[col].dtype in ['float64', 'int64']:
            gb.configure_column(col, valueFormatter=JS_TWO_DECIMAL_FORMATTER, width=80)
    
    # Row styling for favoritter
    gb.configure_grid_options(getRowStyle=JS_FAVORITE_ROW_STYLE)
    
    # Byg grid options
    grid_options = gb.build()
    grid_key = f"favorites_aggrid_{st.session_state.force_rerender_count}"
    
    # Vis tabellen med sikker funktion
    grid_response = safe_aggrid_display(df_display, grid_options, grid_key)
    
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
    
    # Download sektion
    st.subheader("📥 Export")
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = st.session_state.favorites_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download som CSV", 
            csv_data, 
            'mine_favoritter.csv', 
            'text/csv',
            use_container_width=True
        )
    
    with col2:
        json_data = st.session_state.favorites_data.to_json(orient='records', indent=2).encode('utf-8')
        st.download_button(
            "Download som JSON", 
            json_data, 
            'mine_favoritter.json', 
            'application/json',
            use_container_width=True
        )

else:
    st.info("👆 Klik på opdatér-knappen for at hente de seneste priser og nøgletal")
    
    # Vis simpel liste af favoritter
    st.subheader("📋 Nuværende Favoritter")
    
    # Organiser i kolonner for bedre visning
    num_cols = 3
    cols = st.columns(num_cols)
    
    for i, ticker in enumerate(favorite_tickers):
        with cols[i % num_cols]:
            st.write(f"• **{ticker}**")

# Statistik sidebar hvis data findes
if 'favorites_data' in st.session_state and not st.session_state.favorites_data.empty:
    with st.sidebar:
        st.subheader("📊 Portfolio Oversigt")
        df = st.session_state.favorites_data
        
        st.metric("Antal aktier", len(df))
        
        # Beregn gennemsnit hvor muligt
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
                for sector, count in sector_counts.items():
                    if pd.notna(sector):
                        st.write(f"• {sector}: {count}")