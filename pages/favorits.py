# pages/favorites.py
import streamlit as st
import pandas as pd
from core.favorites_manager import load_favorites, save_favorites
from core.data.api_client import get_data_for_favorites
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

st.set_page_config(layout="wide")

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

# Knappen, der udløser API-kald
if st.button("Hent Seneste Data for Favoritter"):
    live_data_df = get_data_for_favorites(favorite_tickers)
    if not live_data_df.empty:
        st.session_state.favorites_data = live_data_df
        st.success("Data opdateret!")

# Vis data med AgGrid hvis tilgængelig
if 'favorites_data' in st.session_state and not st.session_state.favorites_data.empty:
    st.info("Viser senest hentede data. Klik på knappen ovenfor for at opdatere.")
    
    df_display = st.session_state.favorites_data.copy()
    
    # --- VIGTIGT: Formater store tal i Python for at undgå BigInt-fejl i JavaScript ---
    # Formater Market Cap
    if 'Market Cap' in df_display.columns:
        df_display['Market Cap Formatted'] = df_display['Market Cap'].apply(
            lambda x: f"${x/1e9:.2f}B" if pd.notnull(x) and x >= 1e9 else 
                      (f"${x/1e6:.1f}M" if pd.notnull(x) and x >= 1e6 else
                       (f"${x:.2f}" if pd.notnull(x) else "-"))
        )
        df_display = df_display.drop(columns=['Market Cap'])
        df_display = df_display.rename(columns={'Market Cap Formatted': 'Market Cap'})

    # Formater Price
    if 'Price' in df_display.columns:
        df_display['Price Formatted'] = df_display['Price'].apply(
            lambda x: f"${x:.2f}" if pd.notnull(x) else "-"
        )
        df_display = df_display.drop(columns=['Price'])
        df_display = df_display.rename(columns={'Price Formatted': 'Price'})
    # -------------------------------------------------------------------------

    # Tilføj is_favorite kolonne
    df_display['is_favorite'] = True  # Alle aktier i favoritter er naturligvis favoritter
    
    # Reorganiser kolonner så is_favorite kommer først
    cols = ['is_favorite'] + [col for col in df_display.columns if col != 'is_favorite']
    df_display = df_display[cols]
    
    # --- AgGrid setup med genanvendelige komponenter ---
    # JsCode renderers og formatters
    js_button_renderer = JsCode("""
    class FavoriteCellRenderer {
        init(params) {
            this.params = params;
            this.eGui = document.createElement('div');
            this.eGui.style.cssText = 'text-align: center; cursor: pointer; font-size: 1.2em;';
            this.eGui.innerHTML = params.value ? "⭐" : "➕";
            this.eGui.addEventListener('click', () => {
                this.params.node.setDataValue('is_favorite', !this.params.value);
            });
        }
        getGui() { return this.eGui; }
        refresh(params) {
            this.params = params;
            this.eGui.innerHTML = params.value ? "⭐" : "➕";
            return true;
        }
    }
    """)
    
    js_ticker_renderer = JsCode("""
        class TickerLinkRenderer {
            init(params) {
                this.eGui = document.createElement('a');
                this.eGui.innerText = params.value;
                this.eGui.href = `https://finviz.com/quote.ashx?t=${params.value}&ty=l&ta=0&p=w&r=y2`;
                this.eGui.target = '_blank';
                this.eGui.style.cssText = 'color: #ADD8E6; text-decoration: underline;';
            }
            getGui() { return this.eGui; }
        }""")
    
    # --- Fjernet js_market_cap_formatter og js_price_formatter for at undgå BigInt-fejl ---
    # De numeriske værdier er nu tekststrenge, så formattering i JS er ikke nødvendig.
    js_percentage_formatter = JsCode("function(params){return params.value!=null&&!isNaN(params.value)?(parseFloat(params.value)*100).toFixed(1)+'%':'-'}")
    js_two_decimal_formatter = JsCode("function(params){return params.value!=null&&!isNaN(params.value)?parseFloat(params.value).toFixed(2):'-'}")
    
    # Grid builder
    gb = GridOptionsBuilder.from_dataframe(df_display)
    
    # Konfigurer favorit-kolonne
    gb.configure_column(
        "is_favorite", 
        headerName="⭐", 
        cellRenderer=js_button_renderer,
        onCellValueChanged=JsCode("() => {}"),
        width=60, 
        editable=False, 
        lockPosition=True
    )
    
    # Konfigurer andre kolonner (uden valueFormatter for Market Cap og Price)
    if 'Ticker' in df_display.columns:
        gb.configure_column("Ticker", cellRenderer=js_ticker_renderer)
    
    # Market Cap og Price er nu tekststrenge og kræver ingen særlig formattering her
    # Formatering skete i Python ovenfor.
    
    # Formatering for procent-kolonner
    percent_cols = ['Dividend Yield', 'Performance (Quarter)', 'Performance (Year)']
    two_decimal_cols = ['P/E', 'EPS', 'PEG', 'P/S']
    
    for col in percent_cols:
        if col in df_display.columns:
            gb.configure_column(col, valueFormatter=js_percentage_formatter)
    
    for col in two_decimal_cols:
        if col in df_display.columns:
            gb.configure_column(col, valueFormatter=js_two_decimal_formatter)
    
    # Highlight alle rækker som favoritter
    js_row_style = JsCode("function(params){return{'backgroundColor':'rgba(255, 255, 0, 0.1)'}}")
    gb.configure_grid_options(rowStyle=js_row_style)
    
    # Byg og vis tabellen
    grid_options = gb.build()
    grid_key = f"favorites_aggrid_{st.session_state.force_rerender_count}"

    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        key=grid_key,
        allow_unsafe_jscode=True,
        theme="streamlit-dark",
        fit_columns_on_grid_load=True,
        height=600,
        update_on=['cellValueChanged'],
    )
    
    # --- Håndter klik på ⭐-ikonet (tilpasset favorites.py logik) ---
    if grid_response and grid_response.get('data') is not None:
        updated_df = grid_response['data']
        
        # Find tickers der er fjernet fra favoritter (is_favorite = False)
        tickers_in_view = set(df_display['Ticker']) # Alle tickers i denne visning er oprindeligt favoritter
        favorites_in_view_after_change = set(updated_df[updated_df['is_favorite'] == True]['Ticker'])
        
        # Tickers der er fjernet er dem der var der før, men ikke er der nu
        removed_tickers = tickers_in_view - favorites_in_view_after_change
        
        if removed_tickers:
            # Opdater den globale favoritliste
            updated_favorites = [t for t in st.session_state.favorites if t not in removed_tickers]
            st.session_state.favorites = sorted(updated_favorites)
            save_favorites(st.session_state.favorites)
            
            # Fjern de fjernede aktier fra den cachede data
            if 'favorites_data' in st.session_state:
                st.session_state.favorites_data = st.session_state.favorites_data[
                    ~st.session_state.favorites_data['Ticker'].isin(removed_tickers)
                ]
            
            # Signalér til andre sider og tving en opdatering af denne side
            st.session_state.force_favorites_update = True
            st.session_state.force_rerender_count += 1
            
            st.success(f"Fjernede {', '.join(removed_tickers)} fra favoritter.")
            st.rerun()

else:
    st.write("Klik på opdatér-knappen for at hente de seneste priser og nøgletal.")
    
    # Vis simpel liste af favoritter hvis ingen data
    st.subheader("Nuværende Favoritter")
    for i, ticker in enumerate(favorite_tickers, 1):
        st.write(f"{i}. {ticker}")

# Download knap
if 'favorites_data' in st.session_state and not st.session_state.favorites_data.empty:
    csv_data = st.session_state.favorites_data.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download favoritter som CSV", 
        csv_data, 
        'mine_favoritter.csv', 
        'text/csv'
    )