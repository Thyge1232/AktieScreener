# pages/valuation.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.valuation.valuation_engine import ComprehensiveValuationEngine
from core.favorites_manager import load_favorites
from utils.validation import safe_aggrid_display
from utils.aggrid_helpers import JS_PRICE_FORMATTER, JS_PERCENTAGE_FORMATTER
import logging

logger = logging.getLogger(__name__)

st.set_page_config(layout="wide", page_title="Værdiansættelse")

# --- Robuste Hjælpefunktioner med Sikker Dataadgang ---

def display_company_profile(profile):
    """Viser virksomhedsprofilen sikkert vha. getattr."""
    if not profile: return
    with st.sidebar:
        st.subheader("🏢 Virksomhedsprofil")
        company_type = getattr(profile, 'company_type', None)
        st.write(f"**Type:** {company_type.value if company_type else 'N/A'}")
        st.write(f"**Sektor:** {getattr(profile, 'sector', 'N/A')}")
        st.write(f"**Industri:** {getattr(profile, 'industry', 'N/A')}")
        st.write(f"**Markeds Cap:** ${getattr(profile, 'market_cap', 0):,.0f}")
        st.write(f"**Beta:** {getattr(profile, 'beta', 0):.2f}")

def display_wacc_analysis(wacc_data):
    """Viser WACC-analyse."""
    if not wacc_data: return
    st.subheader("⚖️ WACC Analyse")
    col1, col2, col3 = st.columns(3)
    col1.metric("WACC", f"{wacc_data.get('wacc', 0):.2%}")
    col2.metric("Cost of Equity", f"{wacc_data.get('cost_of_equity', 0):.2%}")
    col3.metric("Cost of Debt (After Tax)", f"{wacc_data.get('after_tax_cost_of_debt', 0):.2%}")

def display_dcf_analysis(dcf_data):
    """Viser DCF-analyse med graf og detaljer."""
    if not dcf_data or dcf_data.get('error'):
        st.warning("DCF-analyse kunne ikke gennemføres.")
        return
    st.subheader("💰 DCF Analyse")
    col1, col2, col3 = st.columns(3)
    col1.metric("Fair Value (DCF)", f"${dcf_data.get('value_per_share', 0):.2f}")
    col2.metric("Enterprise Value", f"${dcf_data.get('enterprise_value', 0):,.0f}")
    col3.metric("Terminal Value %", f"{dcf_data.get('terminal_value_percentage', 0):.1%}")
    
    projected_fcf = dcf_data.get('projected_fcf', [])
    if projected_fcf:
        df_fcf = pd.DataFrame(projected_fcf)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_fcf['year'], y=df_fcf['fcf'], name='Projekteret FCF'))
        fig.update_layout(title="Free Cash Flow Projektion", yaxis_title="USD")
        st.plotly_chart(fig, use_container_width=True)

def display_comparable_analysis(comparable_data):
    """Viser sammenligningsværdiansættelse."""
    if not comparable_data: return
    st.subheader("🔍 Sammenligningsværdiansættelse")
    methods = ['pe_comparable', 'ev_ebitda_comparable', 'price_to_book']
    cols = st.columns(len(methods))
    for i, method_key in enumerate(methods):
        method_data = comparable_data.get(method_key, {})
        fair_value = method_data.get('fair_value', 0)
        method_name = method_data.get('method', method_key.replace('_', ' ').title())
        cols[i].metric(method_name, f"${fair_value:.2f}" if fair_value > 0 else "N/A")

def display_risk_assessment(risk_data):
    """Viser risikovurdering."""
    if not risk_data: return
    st.subheader("⚠️ Risikovurdering")
    risk_level_enum = risk_data.get('risk_level')
    risk_level = risk_level_enum.value.title() if risk_level_enum else "Ukendt"
    risk_score = risk_data.get('overall_risk_score', 0)
    st.metric("Samlet Risiko", f"{risk_level} ({risk_score:.0f}/100)")

# --- Hovedlogik ---
st.title("🎯 Detaljeret Værdiansættelse")

if 'valuation_engine' not in st.session_state:
    st.session_state.valuation_engine = ComprehensiveValuationEngine()
valuation_engine = st.session_state.valuation_engine

favorite_tickers = load_favorites()
if not favorite_tickers:
    st.info("Tilføj aktier til dine favoritter for at kunne værdiansætte dem.")
    st.stop()

selected_tickers = st.multiselect("Vælg aktier:", favorite_tickers, default=favorite_tickers[:1])

if not selected_tickers:
    st.info("Vælg mindst én aktie.")
    st.stop()

if st.button("🚀 Udfør Værdiansættelse", use_container_width=True):
    all_results = []
    total = len(selected_tickers)
    progress_bar = st.progress(0, text="Starter...")
    status_text = st.empty()

    def progress_callback(message: str):
        status_text.text(message)

    for i, ticker in enumerate(selected_tickers):
        progress_bar.progress((i) / total, text=f"Behandler {ticker} ({i+1}/{total})...")
        result = valuation_engine.perform_comprehensive_valuation(ticker, progress_callback=progress_callback)
        all_results.append(result)
    
    progress_bar.progress(1.0, text="Analyse fuldført!")
    st.session_state.valuation_results = all_results
    st.rerun()

if 'valuation_results' in st.session_state:
    all_results = st.session_state.valuation_results
    
    successful_results = [res for res in all_results if 'error' not in res]
    failed_results = [res for res in all_results if 'error' in res]

    if failed_results:
        st.subheader("❌ Fejlede Værdiansættelser")
        for res in failed_results:
            st.error(f"**{res.get('ticker', 'Ukendt')}**: {res.get('error')}")

    if not successful_results:
        st.warning("Ingen aktier kunne værdiansættes. Prøv igen eller tjek dine data.")
        st.stop()

    st.subheader("📊 Hurtig Oversigt")
    quick_data = []
    for res in successful_results:
        profile = res.get('company_profile')
        company_type = getattr(profile, 'company_type', None)
        quick_data.append({
            'Ticker': res.get('ticker'),
            'Pris': res.get('current_price'),
            'Fair Value': res.get('fair_value_weighted'),
            'Opside': res.get('upside_potential'),
            'WACC': res.get('wacc_analysis', {}).get('wacc'),
            'Type': company_type.value if company_type else 'N/A'
        })
    
    df_quick = pd.DataFrame(quick_data)
    if not df_quick.empty:
        from st_aggrid import GridOptionsBuilder
        gb = GridOptionsBuilder.from_dataframe(df_quick)
        gb.configure_column('Pris', valueFormatter=JS_PRICE_FORMATTER)
        gb.configure_column('Fair Value', valueFormatter=JS_PRICE_FORMATTER)
        gb.configure_column('Opside', valueFormatter=JS_PERCENTAGE_FORMATTER)
        gb.configure_column('WACC', valueFormatter=JS_PERCENTAGE_FORMATTER)
        safe_aggrid_display(df_quick, gb.build(), "valuation_overview")

    st.divider()
    st.subheader("🔍 Detaljeret Analyse")
    
    ticker_tabs = st.tabs([res['ticker'] for res in successful_results])
    
    for tab, result in zip(ticker_tabs, successful_results):
        with tab:
            st.header(f"Analyse for {result['ticker']}")
            display_company_profile(result.get('company_profile'))
            
            upside = result.get('upside_potential', 0)
            col1, col2, col3 = st.columns(3)
            col1.metric("Nuværende Pris", f"${result.get('current_price', 0):.2f}")
            col2.metric("Vægtet Fair Value", f"${result.get('fair_value_weighted', 0):.2f}")
            col3.metric("Potentiel Opside", f"{upside:.1%}", delta_color="off" if upside == 0 else ("normal" if upside > 0 else "inverse"))
            
            st.divider()
            display_wacc_analysis(result.get('wacc_analysis'))
            st.divider()
            display_dcf_analysis(result.get('valuation_methods', {}).get('dcf'))
            st.divider()
            display_comparable_analysis(result.get('valuation_methods'))
            st.divider()
            display_risk_assessment(result.get('risk_assessment'))