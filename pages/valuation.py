# pages/valuation.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from core.valuation.valuation_engine import ComprehensiveValuationEngine, get_valuation_data
from core.favorites_manager import load_favorites
# --- BRUG af utils ---
from utils.validation import safe_aggrid_display # Importeret fra utils
from utils.aggrid_helpers import ( # Importeret fra utils
    JS_PRICE_FORMATTER,
    JS_PERCENTAGE_FORMATTER,
    JS_TWO_DECIMAL_FORMATTER
)
# --------------------
import logging

logger = logging.getLogger(__name__)

st.set_page_config(layout="wide", page_title="Værdiansættelse")

# Initialiser værdiansættelsesmotoren
valuation_engine = ComprehensiveValuationEngine()

# --- Hjælpefunktioner ---
def display_company_profile(profile):
    """Viser virksomhedsprofilen i en sidebjælke."""
    if not profile:
        return
    with st.sidebar:
        st.subheader("🏢 Virksomhedsprofil")
        st.write(f"**Type:** {profile.company_type.value}")
        st.write(f"**Sektor:** {profile.sector}")
        st.write(f"**Industri:** {profile.industry}")
        st.write(f"**Markeds Cap:** ${profile.market_cap:,.0f}")
        st.write(f"**Beta:** {profile.beta:.2f}")
        st.write(f"**Gæld/Equity:** {profile.debt_to_equity:.2f}")

def display_wacc_analysis(wacc_data):
    """Viser WACC-analyse."""
    if not wacc_data:
        return
    st.subheader("⚖️ WACC Analyse")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("WACC", f"{wacc_data.get('wacc', 0):.2%}")
    with col2:
        st.metric("Cost of Equity", f"{wacc_data.get('cost_of_equity', 0):.2%}")
    with col3:
        st.metric("Cost of Debt (After Tax)", f"{wacc_data.get('after_tax_cost_of_debt', 0):.2%}")
    with col4:
        st.metric("Debt Weight", f"{wacc_data.get('debt_weight', 0):.2%}")
    
    # Vis risikotilpasninger hvis tilgængelige
    adjustments = wacc_data.get('risk_adjustments', {})
    if adjustments:
        st.write("**Risikotilpasninger:**")
        for key, value in adjustments.items():
            if key != 'total_adjustment' and value != 0:
                st.write(f"- {key.replace('_', ' ').title()}: {value:.2%}")

def display_dcf_analysis(dcf_data):
    """Viser DCF-analyse med graf og detaljer."""
    if not dcf_data:
        return
    st.subheader("💰 DCF Analyse")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Fair Value (DCF)", f"${dcf_data.get('value_per_share', 0):.2f}")
    with col2:
        st.metric("Enterprise Value", f"${dcf_data.get('enterprise_value', 0):,.0f}")
    with col3:
        st.metric("Terminal Value %", f"{dcf_data.get('terminal_value_percentage', 0):.1%}")
    
    # Vis antagelser
    assumptions = dcf_data.get('assumptions', {})
    if assumptions:
        st.write("**Antagelser:**")
        ass_cols = st.columns(3)
        ass_cols[0].write(f"- WACC: {assumptions.get('wacc', 0):.2%}")
        ass_cols[1].write(f"- Terminal Growth: {assumptions.get('terminal_growth', 0):.2%}")
        ass_cols[2].write(f"- År: {assumptions.get('projection_years', 0)}")

    # Cash Flow projektion graf
    projected_fcf = dcf_data.get('projected_fcf', [])
    if projected_fcf:
        years = [item['year'] for item in projected_fcf]
        fcfs = [item['fcf'] for item in projected_fcf]
        pv_fcfs = [item['pv_fcf'] for item in projected_fcf]
        
        fig_dcf = go.Figure()
        fig_dcf.add_trace(go.Bar(x=years, y=fcfs, name='Projekteret FCF', marker_color='lightblue'))
        fig_dcf.add_trace(go.Scatter(x=years, y=pv_fcfs, mode='lines+markers', name='PV FCF', line=dict(color='orange')))
        fig_dcf.update_layout(
            title="Free Cash Flow Projektion",
            xaxis_title="År", 
            yaxis_title="USD",
            barmode='group'
        )
        st.plotly_chart(fig_dcf, use_container_width=True)

def display_comparable_analysis(comparable_data):
    """Viser sammenligningsværdiansættelse."""
    if not comparable_data:
        return
    st.subheader("🔍 Sammenligningsværdiansættelse")
    methods = ['pe_comparable', 'ev_ebitda_comparable', 'price_to_book']
    cols = st.columns(len(methods))
    for i, method_key in enumerate(methods):
        method_data = comparable_data.get(method_key, {})
        with cols[i]:
            fair_value = method_data.get('fair_value', 0)
            method_name = method_data.get('method', method_key)
            st.metric(method_name, f"${fair_value:.2f}" if fair_value > 0 else "N/A")

def display_risk_assessment(risk_data):
    """Viser risikovurdering."""
    if not risk_data:
        return
    st.subheader("⚠️ Risikovurdering")
    risk_level = risk_data.get('risk_level', {}).get('value', 'Unknown')
    risk_score = risk_data.get('overall_risk_score', 0)
    st.metric("Samlet Risiko", f"{risk_level.title()} ({risk_score:.0f}/100)")
    
    breakdown = risk_data.get('risk_breakdown', {})
    if breakdown:
        st.write("**Risikokategorier:**")
        risk_cols = st.columns(len(breakdown))
        for i, (category, score) in enumerate(breakdown.items()):
            with risk_cols[i]:
                st.metric(category.replace('_', ' ').title(), f"{score:.0f}")
    
    key_factors = risk_data.get('key_risk_factors', [])
    if key_factors:
        st.write("**Nøglerisici:**")
        for factor in key_factors[:3]: # Vis top 3
            st.write(f"- {factor}")
    
    mitigations = risk_data.get('risk_mitigation_suggestions', [])
    if mitigations:
        st.write("**Risikomindskende foranstaltninger:**")
        for suggestion in mitigations:
            st.write(f"- {suggestion}")

def display_sensitivity_analysis(sensitivity_data):
    """Viser sensitivitetsanalyse."""
    if not sensitivity_data:
        return
    st.subheader("📈 Sensitivitetsanalyse")
    # Dette kan udvides med interaktive plots
    st.json(sensitivity_data) # Foreløbig simpel visning

# --- Hovedlogik ---
st.title("🎯 Detaljeret Værdiansættelse")

# Synkroniser med favoritter
favorite_tickers = load_favorites()
if not favorite_tickers:
    st.info("Du har ingen favoritter. Tilføj nogle i 'Mine Favoritter' siden.")
    st.stop()

# Vælg aktie(r) til værdiansættelse
selected_tickers = st.multiselect("Vælg aktier til værdiansættelse:", favorite_tickers, default=favorite_tickers[:1])

if not selected_tickers:
    st.info("Vælg mindst én aktie for at starte værdiansættelsen.")
    st.stop()

# Progress bar og status
progress_bar = st.progress(0)
status_text = st.empty()

def update_progress(message):
    """Opdaterer progress bar og status tekst."""
    # Simpel logik - i praksis skal du kende antallet af trin
    status_text.text(message)
    # progress_bar.progress(...) - kan opdateres dynamisk hvis nødvendigt

# Knap til at udføre værdiansættelse
if st.button("🚀 Udfør Værdiansættelse", use_container_width=True):
    results = []
    total = len(selected_tickers)
    for i, ticker in enumerate(selected_tickers):
        try:
            update_progress(f"Værdiansætter {ticker} ({i+1}/{total})...")
            result = valuation_engine.perform_comprehensive_valuation(
                ticker, 
                progress_callback=update_progress # Send status tilbage
            )
            if result and 'error' not in result:
                results.append(result)
            else:
                st.error(f"Fejl ved værdiansættelse af {ticker}: {result.get('error', 'Ukendt fejl')}")
        except Exception as e:
            logger.error(f"Uventet fejl ved værdiansættelse af {ticker}: {e}")
            st.error(f"Uventet fejl ved værdiansættelse af {ticker}")
    
    progress_bar.empty()
    status_text.empty()
    
    if results:
        st.session_state.valuation_results = results
        st.success(f"✅ Værdiansættelse færdig for {len(results)} aktier!")
        st.rerun() # Genindlæs siden for at vise resultater

# Vis resultater hvis de findes
if 'valuation_results' in st.session_state and st.session_state.valuation_results:
    results = st.session_state.valuation_results
    
    # Hurtig oversigtstab - BRUGER AgGrid med hjælpere
    st.subheader("📊 Hurtig Oversigt")
    quick_data = []
    for res in results:
        quick_data.append({
            'Ticker': res['ticker'],
            'Pris': res['current_price'], # Gem som tal
            'Fair Value': res['fair_value_weighted'], # Gem som tal
            'Opside': res['upside_potential'], # Gem som tal
            'WACC': res.get('wacc_analysis', {}).get('wacc', 0), # Gem som tal
            'Type': res.get('company_profile', {}).get('company_type', {}).get('value', 'N/A')
        })
    
    df_quick = pd.DataFrame(quick_data)
    if not df_quick.empty:
        # --- AgGrid konfiguration for hurtig oversigt ---
        from st_aggrid import GridOptionsBuilder # Importer her for klarhed
        gb_quick = GridOptionsBuilder.from_dataframe(df_quick)
        
        # Formatering for numeriske kolonner - BRUGER hjælpere
        gb_quick.configure_column('Pris', valueFormatter=JS_PRICE_FORMATTER) # <--- BRUGT
        gb_quick.configure_column('Fair Value', valueFormatter=JS_PRICE_FORMATTER) # <--- BRUGT
        gb_quick.configure_column('Opside', valueFormatter=JS_PERCENTAGE_FORMATTER) # <--- BRUGT
        gb_quick.configure_column('WACC', valueFormatter=JS_PERCENTAGE_FORMATTER) # <--- BRUGT
        
        grid_options_quick = gb_quick.build()
        grid_key_quick = "valuation_quick_overview"
        
        # Vis tabellen med sikker funktion - BRUGER hjælperen
        safe_aggrid_display(df_quick, grid_options_quick, grid_key_quick) # <--- BRUGT
    else:
        st.info("Ingen data at vise i oversigten.")

    # Detaljeret analyse for hver aktie
    st.divider()
    st.subheader("🔍 Detaljeret Analyse")
    
    # Brug tabs for hver aktie
    ticker_tabs = st.tabs([res['ticker'] for res in results])
    
    for i, (tab, result) in enumerate(zip(ticker_tabs, results)):
        with tab:
            ticker = result['ticker']
            st.header(f"📈 {ticker}")
            
            # Vis profil i sidebjælke
            display_company_profile(result.get('company_profile'))
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Nuværende Pris", f"${result['current_price']:.2f}")
                st.metric("Vægtet Fair Value", f"${result['fair_value_weighted']:.2f}")
            with col2:
                upside = result['upside_potential']
                st.metric("Potentiel Opside", f"{upside:.1%}", 
                          delta_color="normal" if upside > 0 else "inverse")
                # Investeringsanbefaling
                if upside > 0.15:
                    st.success("🟢 **KØB** - Høj opside")
                elif upside > 0.05:
                    st.info("🟡 **HOLD** - Moderat opside")
                else:
                    st.warning("🔴 **OVERVEJ SALG** - Begrænset opside")
            
            # Vis de individuelle komponenter
            methods = result.get('valuation_methods', {})
            weights = result.get('method_weights', {})
            
            # WACC
            display_wacc_analysis(result.get('wacc_analysis'))
            
            # DCF
            display_dcf_analysis(methods.get('dcf'))
            
            # Sammenligningsværdiansættelse
            display_comparable_analysis(methods)
            
            # Risikovurdering
            display_risk_assessment(result.get('risk_assessment'))
            
            # Sensitivitetsanalyse (kan udvides)
            # display_sensitivity_analysis(methods.get('dcf', {}).get('sensitivity_analysis'))

            # Vis vægtninger
            st.subheader("⚖️ Metodevægtninger")
            weight_items = list(weights.items())
            if weight_items:
                w_cols = st.columns(len(weight_items))
                for j, (method, weight) in enumerate(weight_items):
                    with w_cols[j]:
                        st.metric(method.upper(), f"{weight:.0%}")

    # Download sektion
    st.divider()
    st.subheader("📥 Export")
    if st.button("Download Resultater som CSV"):
        try:
            # Konverter komplekse objekter til strenge
            export_results = []
            for res in results:
                export_res = res.copy()
                # Fjern komplekse objekter der ikke kan serialiseres direkte
                export_res.pop('company_profile', None)
                export_res.pop('financial_inputs', None)
                export_res.pop('valuation_methods', None) # Kan konverteres hvis nødvendigt
                export_res.pop('wacc_analysis', None) # Kan konverteres hvis nødvendigt
                export_res.pop('risk_assessment', None) # Kan konverteres hvis nødvendigt
                # Tilføj simple værdier fra komplekse objekter
                export_res['company_type'] = res.get('company_profile', {}).get('company_type', {}).get('value', 'N/A')
                export_res['wacc'] = res.get('wacc_analysis', {}).get('wacc', 0)
                export_results.append(export_res)
            
            df_export = pd.DataFrame(export_results)
            csv_data = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download CSV",
                csv_data,
                f"vaerdiansaettelse_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Fejl ved eksport: {e}")

else:
    st.info("Klik 'Udfør Værdiansættelse' for at analysere de valgte aktier.")
