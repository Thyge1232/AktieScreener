# pages/favorites.py - Rettet version
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.favorites_manager import load_favorites, save_favorites
from core.data.api_client import get_data_for_favorites
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from utils.validation import safe_aggrid_display
from utils.aggrid_helpers import (
    JS_FAVORITE_CELL_RENDERER,
    JS_TICKER_LINK_RENDERER,
    JS_PERCENTAGE_FORMATTER,
    JS_TWO_DECIMAL_FORMATTER,
    JS_FAVORITE_ROW_STYLE
)

# Import værdiansættelse med fejlhåndtering
try:
    from core.valuation.valuation_engine import get_valuation_data
    VALUATION_AVAILABLE = True
except ImportError as e:
    st.error(f"Værdiansættelsesmodul kunne ikke importeres: {e}")
    VALUATION_AVAILABLE = False

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

def safe_get_valuation_data(tickers):
    """Sikker wrapper for værdiansættelse"""
    if not VALUATION_AVAILABLE:
        st.error("⚠️ Værdiansættelsesmodul ikke tilgængeligt")
        return pd.DataFrame()
    
    try:
        return get_valuation_data(tickers)
    except Exception as e:
        st.error(f"❌ Fejl ved værdiansættelse: {e}")
        return pd.DataFrame()

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
    valuation_disabled = not VALUATION_AVAILABLE
    if st.button("🎯 Hent Værdiansættelse", use_container_width=True, disabled=valuation_disabled):
        if 'favorites_data' in st.session_state and not st.session_state.favorites_data.empty:
            with st.spinner("Udfører værdiansættelse..."):
                try:
                    # Begræns til 3 aktier for API-grænser og stabilitet
                    limited_tickers = favorite_tickers[:3]
                    st.info(f"🎯 Analyserer de første {len(limited_tickers)} aktier: {', '.join(limited_tickers)}")
                    
                    valuation_data = safe_get_valuation_data(limited_tickers)
                    if not valuation_data.empty:
                        st.session_state.valuation_data = valuation_data
                        st.success(f"🎯 Værdiansættelse klar for {len(valuation_data)} aktier")
                    else:
                        st.warning("⚠️ Ingen værdiansættelsesdata kunne hentes")
                except Exception as e:
                    st.error(f"❌ Fejl ved værdiansættelse: {e}")
        else:
            st.warning("⚠️ Opdater først grunddata")

with col3:
    if valuation_disabled:
        st.error("⚠️ Værdiansættelse ikke tilgængelig - tjek import-fejl")
    elif 'favorites_data' in st.session_state:
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

# Værdiansættelsessektion - FORBEDRET FEJLHÅNDTERING
if 'valuation_data' in st.session_state and not st.session_state.valuation_data.empty:
    st.divider()
    st.header("🎯 Værdiansættelse Resultater")
    
    valuation_df = st.session_state.valuation_data
    
    # Sikkerhedstjek for kolonner
    required_cols = ['Ticker', 'Current_Price', 'Fair_Value', 'Upside_Pct']
    missing_cols = [col for col in required_cols if col not in valuation_df.columns]
    
    if missing_cols:
        st.error(f"⚠️ Manglende kolonner i værdiansættelsesdata: {missing_cols}")
        st.write("Debug - Tilgængelige kolonner:", list(valuation_df.columns))
    else:
        # Hurtig oversigt øverst - med fejlhåndtering
        col1, col2, col3 = st.columns(3)
        
        try:
            with col1:
                if 'Upside_Pct' in valuation_df.columns and not valuation_df['Upside_Pct'].isna().all():
                    avg_upside = valuation_df['Upside_Pct'].mean()
                    st.metric("Gennemsnit Opside", f"{avg_upside:.1%}")
                else:
                    st.metric("Gennemsnit Opside", "N/A")
            
            with col2:
                if 'Upside_Pct' in valuation_df.columns and not valuation_df['Upside_Pct'].isna().all():
                    best_idx = valuation_df['Upside_Pct'].idxmax()
                    if pd.notna(best_idx):
                        best_stock = valuation_df.loc[best_idx]
                        st.metric("Bedste Mulighed", 
                                f"{best_stock['Ticker']} (+{best_stock['Upside_Pct']:.1%})")
                    else:
                        st.metric("Bedste Mulighed", "N/A")
                else:
                    st.metric("Bedste Mulighed", "N/A")
            
            with col3:
                if 'WACC' in valuation_df.columns and not valuation_df['WACC'].isna().all():
                    avg_wacc = valuation_df['WACC'].mean()
                    st.metric("Gennemsnit WACC", f"{avg_wacc:.2%}")
                else:
                    st.metric("Gennemsnit WACC", "N/A")
        
        except Exception as e:
            st.warning(f"Fejl ved beregning af metrics: {e}")
        
        # Tab layout for værdiansættelse
        val_tab1, val_tab2, val_tab3 = st.tabs(["📊 Oversigt", "💰 DCF Analyse", "📈 Scenarier"])
        
        with val_tab1:
            try:
                # Vis værdiansættelsesresultater i tabel
                display_cols = ['Ticker', 'Current_Price', 'Fair_Value', 'Upside_Pct', 'Company_Type', 'WACC']
                available_cols = [col for col in display_cols if col in valuation_df.columns]
                
                if available_cols:
                    display_data = valuation_df[available_cols].copy()
                    
                    # Formatter værdier for bedre visning - med fejlhåndtering
                    if 'Current_Price' in display_data.columns:
                        display_data['Current_Price'] = display_data['Current_Price'].apply(
                            lambda x: f"${x:.2f}" if pd.notna(x) and x > 0 else "N/A"
                        )
                    if 'Fair_Value' in display_data.columns:
                        display_data['Fair_Value'] = display_data['Fair_Value'].apply(
                            lambda x: f"${x:.2f}" if pd.notna(x) and x > 0 else "N/A"
                        )
                    if 'Upside_Pct' in display_data.columns:
                        display_data['Upside_Pct'] = display_data['Upside_Pct'].apply(
                            lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
                        )
                    if 'WACC' in display_data.columns:
                        display_data['WACC'] = display_data['WACC'].apply(
                            lambda x: f"{x:.2%}" if pd.notna(x) else "N/A"
                        )
                    
                    st.dataframe(display_data, use_container_width=True)
                else:
                    st.warning("Ingen data at vise i oversigtstabellen")
                
                # Vis detaljerede anbefalinger
                for idx, row in valuation_df.iterrows():
                    ticker = row.get('Ticker', 'N/A')
                    with st.expander(f"📈 {ticker} - Detaljeret Analyse"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            current_price = row.get('Current_Price', 0)
                            fair_value = row.get('Fair_Value', 0)
                            upside = row.get('Upside_Pct', 0)
                            
                            st.metric("Nuværende Pris", 
                                    f"${current_price:.2f}" if current_price > 0 else "N/A")
                            st.metric("Fair Value", 
                                    f"${fair_value:.2f}" if fair_value > 0 else "N/A")
                            
                            if pd.notna(upside):
                                st.metric("Potentiel Opside", f"{upside:.1%}", 
                                        delta_color="normal" if upside > 0 else "inverse")
                            else:
                                st.metric("Potentiel Opside", "N/A")
                        
                        with col2:
                            st.write(f"**Virksomhedstype:** {row.get('Company_Type', 'N/A')}")
                            st.write(f"**Anbefalede metoder:** {row.get('Recommended_Methods', 'N/A')}")
                            
                            wacc = row.get('WACC', 0)
                            st.write(f"**WACC:** {wacc:.2%}" if pd.notna(wacc) else "**WACC:** N/A")
                            
                            # Investeringsanbefaling
                            if pd.notna(upside):
                                if upside > 0.15:
                                    st.success("🟢 **KØB** - Høj opside")
                                elif upside > 0.05:
                                    st.info("🟡 **HOLD** - Moderat opside")
                                else:
                                    st.warning("🔴 **OVERVEJ SALG** - Begrænset opside")
                            else:
                                st.info("⚪ **MANGLENDE DATA** - Kan ikke vurderes")
                                
            except Exception as e:
                st.error(f"Fejl i oversigtstab: {e}")
                st.write("Debug info:", valuation_df.dtypes)
        
        with val_tab2:
            try:
                # DCF Analyse visualisering
                if len(valuation_df) > 0:
                    ticker_options = valuation_df['Ticker'].tolist()
                    selected_ticker = st.selectbox("Vælg aktie for DCF analyse:", ticker_options)
                    
                    ticker_row = valuation_df[valuation_df['Ticker'] == selected_ticker]
                    if not ticker_row.empty:
                        ticker_data = ticker_row.iloc[0]
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            wacc = ticker_data.get('WACC', 0)
                            terminal_growth = ticker_data.get('Terminal_Growth', 0.025)
                            st.metric("WACC", f"{wacc:.2%}" if pd.notna(wacc) else "N/A")
                            st.metric("Terminal Growth", f"{terminal_growth:.1%}" if pd.notna(terminal_growth) else "N/A")
                        
                        with col2:
                            current_price = ticker_data.get('Current_Price', 0)
                            fair_value = ticker_data.get('Fair_Value', 0)
                            st.metric("Markedspris", f"${current_price:.2f}" if current_price > 0 else "N/A")
                            
                            if fair_value > 0 and current_price > 0:
                                delta_val = fair_value - current_price
                                st.metric("DCF Værdi", f"${fair_value:.2f}", 
                                        delta=f"${delta_val:.2f}")
                            else:
                                st.metric("DCF Værdi", "N/A")
                        
                        # Cash Flow projektion hvis tilgængelig
                        projected_fcf_str = ticker_data.get('Projected_FCF', '[]')
                        if projected_fcf_str and projected_fcf_str != '[]':
                            try:
                                projected_fcf = eval(projected_fcf_str)
                                if projected_fcf and len(projected_fcf) > 0:
                                    years = list(range(1, len(projected_fcf) + 1))
                                    
                                    fig_dcf = go.Figure()
                                    fig_dcf.add_trace(go.Bar(
                                        x=years, 
                                        y=projected_fcf, 
                                        name='Projekteret FCF',
                                        marker_color='lightblue'
                                    ))
                                    fig_dcf.update_layout(
                                        title=f"{selected_ticker} - Free Cash Flow Projektion",
                                        xaxis_title="År", 
                                        yaxis_title="FCF (USD)",
                                        showlegend=False
                                    )
                                    st.plotly_chart(fig_dcf, use_container_width=True)
                                else:
                                    st.info("Ingen cash flow projektion tilgængelig")
                            except Exception as e:
                                st.warning(f"Fejl ved visning af cash flow projektion: {e}")
                        else:
                            st.info("Cash flow projektion ikke tilgængelig")
                    else:
                        st.warning(f"Ingen data fundet for {selected_ticker}")
                        
            except Exception as e:
                st.error(f"Fejl i DCF analyse tab: {e}")
        
        with val_tab3:
            try:
                # Scenarioanalyse
                scenario_cols = ['Best_Case', 'Base_Case', 'Worst_Case']
                available_scenario_cols = [col for col in scenario_cols if col in valuation_df.columns]
                
                if available_scenario_cols and len(valuation_df) > 0:
                    ticker_options = valuation_df['Ticker'].tolist()
                    selected_ticker_scenario = st.selectbox("Vælg aktie for scenarie:", 
                                                          ticker_options, key="scenario")
                    
                    ticker_row = valuation_df[valuation_df['Ticker'] == selected_ticker_scenario]
                    if not ticker_row.empty:
                        ticker_scenarios = ticker_row.iloc[0]
                        
                        scenarios = {}
                        for col in available_scenario_cols:
                            value = ticker_scenarios.get(col)
                            if pd.notna(value) and value > 0:
                                scenarios[col.replace('_', ' ')] = value
                        
                        if scenarios:
                            fig_scenarios = go.Figure()
                            colors = ['red', 'blue', 'green']
                            fig_scenarios.add_trace(go.Bar(
                                x=list(scenarios.keys()),
                                y=list(scenarios.values()),
                                marker_color=colors[:len(scenarios)]
                            ))
                            
                            current_price = ticker_scenarios.get('Current_Price', 0)
                            if current_price > 0:
                                fig_scenarios.add_hline(
                                    y=current_price, 
                                    line_dash="dash",
                                    annotation_text=f"Aktuel: ${current_price:.2f}"
                                )
                            
                            fig_scenarios.update_layout(
                                title=f"{selected_ticker_scenario} - Scenarioanalyse",
                                yaxis_title="Værdi per aktie ($)",
                                showlegend=False
                            )
                            st.plotly_chart(fig_scenarios, use_container_width=True)
                            
                            # Scenarie tabel
                            scenario_data = []
                            for scenario_name, value in scenarios.items():
                                pct_change = "N/A"
                                if current_price > 0:
                                    pct_change = f"{((value/current_price)-1):.1%}"
                                
                                scenario_data.append({
                                    'Scenarie': scenario_name,
                                    'Værdi': f"${value:.2f}",
                                    'vs. Aktuel': pct_change
                                })
                            
                            scenario_df = pd.DataFrame(scenario_data)
                            st.dataframe(scenario_df, use_container_width=True)
                        else:
                            st.warning("Ingen gyldige scenarie-data tilgængelig")
                    else:
                        st.warning(f"Ingen data fundet for {selected_ticker_scenario}")
                else:
                    st.info("Scenarioanalyse ikke tilgængelig - manglende data")
                    
            except Exception as e:
                st.error(f"Fejl i scenarie tab: {e}")

        # Download sektion
        st.subheader("📥 Export")
        col1, col2 = st.columns(2)
        
        with col1:
            if 'favorites_data' in st.session_state and not st.session_state.favorites_data.empty:
                try:
                    csv_data = st.session_state.favorites_data.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download grunddata som CSV", 
                        csv_data, 
                        'mine_favoritter.csv', 
                        'text/csv',
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Fejl ved CSV export: {e}")
        
        with col2:
            try:
                valuation_csv = valuation_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Download værdiansættelse som CSV", 
                    valuation_csv, 
                    'vaerdiansoettelse.csv', 
                    'text/csv',
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Fejl ved værdiansættelse CSV export: {e}")

else:
    # Vis værdiansættelse besked hvis data ikke findes
    if 'favorites_data' in st.session_state and not st.session_state.favorites_data.empty and VALUATION_AVAILABLE:
        st.info("🎯 Klik 'Hent Værdiansættelse' knappen for at se detaljeret analyse")
    elif not VALUATION_AVAILABLE:
        st.error("⚠️ Værdiansættelsesmodul ikke tilgængeligt - tjek import-fejl")
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