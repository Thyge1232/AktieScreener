import streamlit as st
import os
import json
import pandas as pd
import io
from datetime import datetime
from typing import Dict, Any, List
import plotly.graph_objects as go
import time



# Importer kernekomponenter
from core.config_loader import ConfigLoader
from core.data.data_fetcher import UniversalDataFetcher
from core.screening.screener import UniversalScreener
from core.valuation.valuation_engine import ValuationEngine
from core.reporting.report_generator import ReportGenerator
from core.reporting.visualization import Visualization
from utils.helper_functions import get_market_for_ticker, format_currency, format_percentage
from utils.sector_analysis import analyze_sector_potential, get_sector_recommendations
from utils.financial_calculations import calculate_piotroski_score

def format_time(seconds):
    """Formaterer sekunder til en læsbar streng (f.eks. '2m 30s')"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

def calculate_eta(start_time, processed, total):
    """Beregner estimeret tid tilbage"""
    elapsed = time.time() - start_time
    if processed == 0:
        return 0
    avg_time = elapsed / processed
    return avg_time * (total - processed)

def initialize_app():
    """Initialiserer app'en og indlæser nødvendige komponenter"""
    st.set_page_config(
        page_title="Professionel Investeringsplatform",
        layout="wide",
        page_icon="💼"
    )
    config_loader = ConfigLoader()
    if 'config_loader' not in st.session_state:
        st.session_state.config_loader = config_loader
    if 'data_fetcher' not in st.session_state:
        st.session_state.data_fetcher = UniversalDataFetcher()
    if 'screener' not in st.session_state:
        st.session_state.screener = UniversalScreener(st.session_state.data_fetcher)
    if 'valuation_engine' not in st.session_state:
        st.session_state.valuation_engine = ValuationEngine()
    if 'report_generator' not in st.session_state:
        st.session_state.report_generator = ReportGenerator()
    if 'visualization' not in st.session_state:
        st.session_state.visualization = Visualization()
    if 'screening_results' not in st.session_state:
        st.session_state.screening_results = {}
    if 'current_ticker' not in st.session_state:
        st.session_state.current_ticker = None
    if 'current_strategy' not in st.session_state:
        st.session_state.current_strategy = "multibagger"

def get_small_cap_tickers(market: List[str]) -> List[str]:
    """Henter small-cap tickers for valgte markeder"""
    tickers = []
    
    # USA small-caps
    if "USA" in market:
        try:
            from finvizfinance.screener.overview import Overview
            foverview = Overview()
            filters_dict = {'Market Cap.': 'Small ($300mln to $2bln)'}
            foverview.set_filter(filters_dict=filters_dict)
            usa_df = foverview.screener_view(verbose=0)
            tickers.extend(usa_df['Ticker'].tolist())
        except Exception as e:
            st.warning(f"Fejl ved hentning af USA small-caps: {str(e)}")
    
    # EU small-caps - FJERN $ FORAN TILKYNDELSENE
    if "Europa" in market:
        eu_tickers = [
            'ALFEN.AS', 'CTP.AS', 'KNX.DE', 'NEM.DE', 'SAE.DE', 'ATOS.PA', 'EL.PA',
            'BAVA.CO', 'GN.CO', 'ROCK-B.CO', 'SINCH.ST', 'THULE.ST', 'ADD.L',
            'DOM.L', 'SPI.L', 'LOGN.SW', 'SOON.SW', 'QTCOM.HE', 'SIE.DE',
            'EQT.ST', 'KINV-B.ST', 'NDA-SE.ST', 'VOLCAR.ST', 'INVE-B.ST',
            'FLS.N', 'WIX.N', 'HUG.L', 'BKG.L', 'BVS.L', 'ASLAK.NO',
            'BWG.L', 'CAKE.L', 'DOTD.L', 'FEVR.L', 'GB00.L'
        ]
        tickers.extend(eu_tickers)
    
    # Asien small-caps
    if "Asien" in market:
        asian_tickers = [
            '9988.HK', 'BABA', 'JD', 'PDD', '0700.HK', '9618.HK',
            '2318.HK', '3690.HK', '9888.HK', '6098.HK'
        ]
        tickers.extend(asian_tickers)
    
    # Emerging Markets
    if "Emerging Markets" in market:
        em_tickers = [
            'ITUB', 'SAN', 'BBVA', 'PBR', 'ELEKTRISKA.IS', 'GVT',
            'ITSA4.SA', 'PETR4.SA', 'VALE', 'CIEL3.SA'
        ]
        tickers.extend(em_tickers)
    
    # FJERN $ FORAN TILKYNDELSENE OG RENS TILKYNDELSER
    cleaned_tickers = []
    for ticker in tickers:
        # Fjern $ foran ticker
        if ticker.startswith('$'):
            ticker = ticker[1:]
        
        # Rens ticker (fjern eventuelle ekstra tegn)
        if '.' in ticker:
            parts = ticker.split('.')
            ticker = f"{parts[0]}.{parts[1][0]}"  # Beholder kun det første tegn efter punktum
        
        cleaned_tickers.append(ticker)
    
    return list(set(cleaned_tickers))  # Fjern dubletter

def format_results(results: List[Dict[str, Any]], profile: Dict[str, Any]) -> pd.DataFrame:
    """Formaterer screening resultater til DataFrame"""
    if not results:
        return pd.DataFrame()
    
    # Konverter til DataFrame
    df = pd.DataFrame(results)
    
    # Sikr at alle nødvendige kolonner findes
    if "sector" in df.columns:
        df["Sektor"] = df["sector"]
    else:
        df["Sektor"] = "Ukendt"
    
    if "country" in df.columns:
        df["Land"] = df["country"]
    else:
        df["Land"] = "Ukendt"
    
    # Tilføj strategy_type
    df["strategy_type"] = profile.get("strategy_type", "multibagger")
    
    # Find den relevante score-kolonne
    score_col = None
    if "multibagger_score" in df.columns:
        score_col = "multibagger_score"
        df = df.rename(columns={"multibagger_score": "Kvalitets Score"})
    elif "value_score" in df.columns:
        score_col = "value_score"
        df = df.rename(columns={"value_score": "Value Score"})
    elif "deep_value_score" in df.columns:
        score_col = "deep_value_score"
        df = df.rename(columns={"deep_value_score": "Deep Value Score"})
    elif "combined_score" in df.columns:
        score_col = "combined_score"
        df = df.rename(columns={"combined_score": "Kombineret Score"})
    
    # Formater kolonner
    if "market_cap" in df.columns:
        df["Markedsværdi"] = df["market_cap"].apply(lambda x: format_currency(x))
    
    if "current_price" in df.columns:
        df["Aktuel pris"] = df["current_price"].apply(lambda x: format_currency(x))
    
    if "revenue_growth" in df.columns:
        df["Omsætning Vækst"] = df["revenue_growth"].apply(format_percentage)
    
    if "eps_growth" in df.columns:
        df["EPS Vækst"] = df["eps_growth"].apply(format_percentage)
    
    if "roe" in df.columns:
        df["ROE"] = df["roe"].apply(format_percentage)
    
    if "peg_ratio" in df.columns:
        df["PEG Ratio"] = df["peg_ratio"].apply(lambda x: f"{x:.2f}" if x else "N/A")
    
    if "dividend_yield" in df.columns:
        df["Dividendeafkast"] = df["dividend_yield"].apply(format_percentage)
    
    # Vælg relevante kolonner
    strategy_type = profile.get("strategy_type", "multibagger")
    if strategy_type == "multibagger":
        columns = [
            "Ticker", "Navn", "Sektor", "Land", "Markedsværdi", "Aktuel pris",
            "Kvalitets Score", "Omsætning Vækst", "EPS Vækst", "ROE", "PEG Ratio"
        ]
    elif strategy_type == "value":
        columns = [
            "Ticker", "Navn", "Sektor", "Land", "Markedsværdi", "Aktuel pris",
            "Value Score", "PE Ratio", "PB Ratio", "Dividendeafkast", "ROE"
        ]
    elif strategy_type == "deep_value":
        columns = [
            "Ticker", "Navn", "Sektor", "Land", "Markedsværdi", "Aktuel pris",
            "Deep Value Score", "PB Ratio", "Cash/Markedsværdi", "ROE"
        ]
    else:  # combined
        columns = [
            "Ticker", "Navn", "Sektor", "Land", "Markedsværdi", "Aktuel pris",
            "Kombineret Score", "Omsætning Vækst", "EPS Vækst", "PE Ratio", "ROE"
        ]
    
    # Sikr at alle kolonner eksisterer
    available_columns = [col for col in columns if col in df.columns]
    
    # Tilføj manglende kolonner med "N/A" værdier
    for col in columns:
        if col not in df.columns:
            df[col] = "N/A"
    
    return df[columns]

def display_screening_results(results: Dict[str, pd.DataFrame]):
    """Viser screening resultater i UI"""
    st.subheader("📊 Screening Resultater")
    
    # Opret tabs for hver profil
    tabs = st.tabs(list(results.keys()))
    
    for i, (profile_name, df) in enumerate(results.items()):
        with tabs[i]:
            if df.empty:
                st.warning("Ingen aktier opfyldte kriterierne for denne profil")
            else:
                # Vis top 10 aktier
                st.subheader("🏆 Top 10 Aktier")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Vis sektordistribution - HÅNDTÉR MANGLENDE SEKTORKOLONNE
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.subheader("📈 Sektorfordeling")
                    
                    # Tjek om "Sektor" kolonnen findes
                    if "Sektor" in df.columns:
                        sector_counts = df["Sektor"].value_counts()
                        for sector, count in sector_counts.items():
                            st.metric(sector, f"{count} aktier")
                    else:
                        st.info("Sektordata ikke tilgængelig")
                
                with col2:
                    # Tjek om "Sektor" kolonnen findes før visualisering
                    if "Sektor" in df.columns:
                        fig = st.session_state.visualization.sector_distribution_chart(df.to_dict('records'))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Sektordistribution ikke tilgængelig")
                
                # Vis scorefordeling
                st.subheader("🔍 Score Fordeling")
                fig = st.session_state.visualization.score_distribution_chart(df.to_dict('records'))
                st.plotly_chart(fig, use_container_width=True)
                
                # Download knap
                output = st.session_state.report_generator.generate_screening_report(
                    df.to_dict('records'), 
                    st.session_state.config_loader.load_strategy_profiles(
                        st.session_state.current_strategy
                    )["profiles"][profile_name]
                )
                
                st.download_button(
                    label="📥 Download Resultater som Excel",
                    data=output.getvalue(),
                    file_name=f"screening_resultater_{profile_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

def display_valuation_results(ticker: str, metrics: Dict[str, Any], result: Dict[str, Any], strategy_type: str):
    """Viser værdiansættelsesresultater i UI"""
    st.subheader(f"📊 Værdiansættelse for {ticker} - {metrics.get('name', '')}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Aktuel pris", format_currency(metrics.get("current_price", 0)))
    with col2:
        st.metric("Fair Value", format_currency(result.get("fair_value_per_share", 0)))
    with col3:
        mos = result.get("margin_of_safety", 0)
        color = "green" if mos > 0 else "red"
        st.metric("Margin of Safety", format_percentage(mos), delta_color=color)
    fig = st.session_state.visualization.valuation_gauge(mos)
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("PropertyParams")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Model Parametre**")
        params = result.get("assumptions", {})
        for param, value in params.items():
            st.write(f"{param.replace('_', ' ').title()}: {value}")
    with col2:
        st.write("**Fundamentale Metrikker**")
        fundamental_metrics = {
            "pe_ratio": "PE Ratio",
            "pb_ratio": "PB Ratio",
            "peg_ratio": "PEG Ratio",
            "roe": "ROE",
            "dividend_yield": "Dividendeafkast",
            "debt_to_equity": "Gæld/Egenkapital"
        }
        for metric, label in fundamental_metrics.items():
            value = metrics.get(metric)
            if value is not None:
                if metric == "dividend_yield":
                    st.write(f"{label}: {format_percentage(value)}")
                elif metric in ["roe", "debt_to_equity"]:
                    st.write(f"{label}: {value:.2f}")
                else:
                    st.write(f"{label}: {value:.2f}")
    st.subheader("💡 Anbefaling")
    if mos > 0.3:
        st.success(f"**KØB** - Stor margin of safety ({format_percentage(mos)})")
        st.balloons()
    elif mos > 0.15:
        st.success(f"**KØB** - God margin of safety ({format_percentage(mos)})")
    elif mos > 0:
        st.info(f"**OVERVEJ** - Lille margin of safety ({format_percentage(mos)})")
    else:
        st.warning(f"**UNDGÅ** - Overpriset med {format_percentage(abs(mos))}")
    if st.checkbox("Vis historisk performance"):
        try:
            hist = st.session_state.data_fetcher.fetch_technical_data(ticker)
            if not hist.empty:
                fig = st.session_state.visualization.historical_performance_chart(ticker, hist)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Ingen historiske data tilgængelig")
        except:
            st.warning("Kunne ikke hente historiske data")

def strategy_screening_tab():
    """UI til strategisk screening med fremdriftsindikator"""
    st.header("📈 Strategi Screening")
    
    # Strategivalg
    strategy_type = st.selectbox(
        "Vælg investeringsstrategi",
        ["multibagger", "value", "deep_value", "combined"],
        format_func=lambda x: {
            "multibagger": "🚀 Multibagger Screening",
            "value": "🔍 Value Screening",
            "deep_value": "💎 Deep Value Screening",
            "combined": "🔄 Kombinerede Strategier"
        }[x],
        key="strategy_type_selector"
    )
    
    # Gem valgt strategi i session state
    st.session_state.current_strategy = strategy_type
    
    # Hent relevante profiler
    config_loader = st.session_state.config_loader
    profiles = config_loader.load_strategy_profiles(strategy_type)["profiles"]
    
    # Profilvalg
    st.subheader("PropertyParams")
    selected_profiles = st.multiselect(
        "Vælg profiler",
        options=list(profiles.keys()),
        default=list(profiles.keys())[:1],
        format_func=lambda x: profiles[x]["name"],
        key="selected_profiles"
    )
    
    # Markedsvalg
    market = st.multiselect(
        "Vælg markeder",
        ["USA", "Europa", "Asien", "Emerging Markets", "Global"],
        default=["USA", "Europa"],
        key="market_selector"
    )
    
    # Avancerede indstillinger
    with st.expander("PropertyParams"):
        if selected_profiles:
            profile = profiles[selected_profiles[0]]
            params = profile["parameters"]
            
            st.write(f"PropertyParams for {profile['name']}")
            
            # Opret to kolonner for parametre
            cols = st.columns(2)
            col_idx = 0
            
            for param, value in params.items():
                with cols[col_idx % 2]:
                    if isinstance(value, bool):
                        new_value = st.checkbox(
                            param.replace('_', ' ').title(),
                            value=value,
                            key=f"{strategy_type}_{param}"
                        )
                    else:
                        new_value = st.number_input(
                            param.replace('_', ' ').title(),
                            value=float(value),
                            key=f"{strategy_type}_{param}"
                        )
                    params[param] = new_value
                    col_idx += 1
    
    # Start screening knap
    if st.button("Start Screening", type="primary", use_container_width=True):
        with st.spinner("Kører screening... Dette kan tage 2-5 minutter."):
            # Hent relevante tickers baseret på markeder
            tickers = get_small_cap_tickers(market)
            total_tickers = len(tickers)
            
            if not tickers:
                st.warning("Ingen tickers fundet for de valgte markeder")
                return
                
            # Vis fremdrift
            progress_bar = st.progress(0)
            status_container = st.empty()
            time_container = st.empty()
            
            # Initialiser tid
            start_time = time.time()
            processed = 0
            
            # Udfør screening for valgte profiler
            all_results = {}
            for profile_name in selected_profiles:
                profile = profiles[profile_name]
                results = []
                
                # Opdater status
                status_container.markdown(f"**Screening med {profile['name']}**\n\nProcesserer tickers...")
                
                # Loop igennem alle tickers
                for i, ticker in enumerate(tickers):
                    # Hent data
                    metrics = st.session_state.data_fetcher.fetch_all_metrics(ticker, strategy_type)
                    
                    # Tjek om aktien opfylder kriterier
                    if metrics and st.session_state.screener._passes_filters(metrics, profile["parameters"]):
                        # Beregn score
                        metrics["score"] = st.session_state.screener.calculate_strategy_score(metrics, profile)
                        results.append(metrics)
                    
                    # Opdater fremdrift
                    processed = i + 1
                    progress = processed / total_tickers
                    progress_bar.progress(progress)
                    
                    # Beregn tid og estimeret tid tilbage
                    elapsed_time = time.time() - start_time
                    avg_time_per_ticker = elapsed_time / processed if processed > 0 else 0
                    estimated_time_remaining = avg_time_per_ticker * (total_tickers - processed)
                    
                    # Opdater status
                    status = f"Processerer ticker {processed}/{total_tickers}"
                    time_info = f"Brugt tid: {format_time(elapsed_time)} | Estimeret tid tilbage: {format_time(estimated_time_remaining)}"
                    
                    status_container.markdown(f"**Screening med {profile['name']}**\n\n{status}")
                    time_container.text(time_info)
                
                if results:
                    # Konverter til DataFrame og tilføj til resultater
                    df = format_results(results, profile)
                    all_results[profile_name] = df
            
            # Vis færdigmeddelelse
            progress_bar.progress(1.0)
            status_container.markdown(f"**Screening fuldført!**\n\nFundet {sum(len(df) for df in all_results.values())} aktier der opfylder kriterierne")
            total_time = time.time() - start_time
            time_container.text(f"Total tid: {format_time(total_time)}")
            
            # Gem resultater i session state
            if all_results:
                st.session_state.screening_results = all_results
                display_screening_results(all_results)
            else:
                st.warning("Ingen aktier opfyldte de valgte kriterier. Prøv at løsne kravene.")

def valuation_tab():
    """UI til værdiansættelse"""
    st.header("💰 Avanceret Værdiansættelse")
    if "screening_results" in st.session_state and st.session_state.screening_results:
        all_results = pd.concat(st.session_state.screening_results.values())
        ticker = st.selectbox(
            "Vælg aktie fra screening resultater", 
            all_results["Ticker"].unique(),
            key="valuation_ticker"
        )
        selected_stock = all_results[all_results["Ticker"] == ticker].iloc[0]
        strategy_type = selected_stock.get("strategy_type", "multibagger")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            ticker = st.text_input("Indtast ticker symbol", "AAPL", key="manual_ticker")
        with col2:
            strategy_type = st.selectbox(
                "Strategitype",
                ["multibagger", "value", "deep_value", "combined"],
                format_func=lambda x: {
                    "multibagger": "🚀 Multibagger",
                    "value": "🔍 Value",
                    "deep_value": "💎 Deep Value",
                    "combined": "🔄 Kombineret"
                }[x],
                key="manual_strategy"
            )
    valuation_models = st.session_state.config_loader.load_valuation_models()
    selected_model = st.selectbox(
        "Vælg værdiansættelsesmodel",
        list(valuation_models.keys()),
        format_func=lambda x: valuation_models[x]["name"],
        key="valuation_model"
    )
    if st.button("Udfør Værdiansættelse", type="primary", use_container_width=True) and ticker:
        with st.spinner(f"Henter data og udfører værdiansættelse for {ticker}..."):
            metrics = st.session_state.data_fetcher.fetch_all_metrics(ticker, strategy_type)
            if not metrics or metrics.get("market_cap", 0) == 0:
                st.error(f"Kunne ikke hente data for {ticker}. Tjek venligst tickeren.")
                return
            result = st.session_state.valuation_engine.evaluate(
                metrics, 
                strategy_type,
                selected_model
            )
            if "error" in result:
                st.error(result["error"])
                return
            display_valuation_results(ticker, metrics, result, strategy_type)
            output = st.session_state.report_generator.generate_valuation_report(
                result, metrics, ticker
            )
            st.download_button(
                label="📥 Download Værdiansættelse som Excel",
                data=output.getvalue(),
                file_name=f"vaerdiansaettelse_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def portfolio_analysis_tab():
    """UI til porteføljeanalyse"""
    st.header("📊 Portfolio Analyse")
    portfolio_file = st.file_uploader("Upload din portefølje (CSV eller Excel)", type=["csv", "xlsx"])
    if portfolio_file:
        try:
            if portfolio_file.name.endswith(".csv"):
                portfolio = pd.read_csv(portfolio_file)
            else:
                portfolio = pd.read_excel(portfolio_file)
            st.success("Portefølje uploadet succesfuldt!")
            st.dataframe(portfolio, use_container_width=True)
            if st.button("Analyser Portefølje", type="primary", use_container_width=True):
                with st.spinner("Udfører porteføljeanalyse..."):
                    portfolio_list = portfolio.to_dict('records')
                    portfolio_data = []
                    for asset in portfolio_list:
                        ticker = asset.get("Ticker") or asset.get("ticker")
                        if ticker:
                            data = st.session_state.data_fetcher.fetch_all_metrics(ticker)
                            if data:
                                portfolio_data.append(data)
                    if not portfolio_data:
                        st.warning("Kunne ikke hente data for nogen aktier i porteføljen")
                        return
                    total_value = sum(asset.get("market_cap", 0) for asset in portfolio_data)
                    st.subheader("📈 Sektorfordeling")
                    sector_counts = {}
                    for asset in portfolio_data:
                        sector = asset.get("sector", "Ukendt")
                        sector_counts[sector] = sector_counts.get(sector, 0) + asset.get("market_cap", 0)
                    sector_percentages = {k: (v/total_value)*100 for k, v in sector_counts.items()}
                    cols = st.columns(3)
                    for i, (sector, percentage) in enumerate(sector_percentages.items()):
                        with cols[i % 3]:
                            st.metric(sector, f"{percentage:.1f}%")
                    fig = st.session_state.visualization.sector_distribution_chart(portfolio_data)
                    st.plotly_chart(fig, use_container_width=True)
                    st.subheader("🔍 Kvalitetsfordeling")
                    quality_scores = []
                    for asset in portfolio_data:
                        if "multibagger_score" in asset:
                            quality_scores.append(asset["multibagger_score"])
                        elif "value_score" in asset:
                            quality_scores.append(asset["value_score"])
                        elif "deep_value_score" in asset:
                            quality_scores.append(asset["deep_value_score"])
                    if quality_scores:
                        avg_score = sum(quality_scores) / len(quality_scores)
                        st.metric("Gennemsnitlig Kvalitets Score", f"{avg_score:.1f}/100")
                        fig = st.session_state.visualization.score_distribution_chart(portfolio_data)
                        st.plotly_chart(fig, use_container_width=True)
                    st.subheader("💡 Portefølje Anbefalinger")
                    market_data = {
                        "sectors": [
                            {"name": "Technology", "performance": 0.18},
                            {"name": "Healthcare", "performance": 0.12},
                            {"name": "Financial Services", "performance": 0.05},
                            {"name": "Consumer Cyclical", "performance": 0.08},
                            {"name": "Energy", "performance": -0.05}
                        ]
                    }
                    recommendations = get_sector_recommendations(portfolio_data, market_data)
                    if recommendations:
                        for rec in recommendations:
                            if rec["type"] == "BUY":
                                st.success(f"**KØB {rec['sector']}** - {rec['rationale']}")
                            else:
                                st.warning(f"**SÆLG {rec['sector']}** - {rec['rationale']}")
                    else:
                        st.info("Ingen specifikke anbefalinger på nuværende tidspunkt")
                    output = st.session_state.report_generator.generate_portfolio_analysis(
                        {"Din Portefølje": portfolio_data}
                    )
                    st.download_button(
                        label="📥 Download Portefølje Analyse som Excel",
                        data=output.getvalue(),
                        file_name=f"portfolio_analyse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        except Exception as e:
            st.error(f"Fejl ved upload af portefølje: {str(e)}")

def market_research_tab():
    """UI til markeds research"""
    st.header("🔍 Markeds Research")
    st.subheader("📈 Sektoranalyse")
    sector_potential = analyze_sector_potential()
    st.write("Sektorer med højest potentiale for multibaggers:")
    cols = st.columns(3)
    for i, (sector, score) in enumerate(sorted(sector_potential.items(), key=lambda x: x[1], reverse=True)):
        with cols[i % 3]:
            st.metric(sector, f"{score}/10")
    sectors = list(sector_potential.keys())
    scores = list(sector_potential.values())
    fig = go.Figure(go.Bar(
        x=sectors,
        y=scores,
        marker_color=['#1f77b4' if s >= 7.0 else '#ff7f0e' for s in scores]
    ))
    fig.update_layout(
        title="Sektor Potentiale",
        xaxis_title="Sektor",
        yaxis_title="Potentiale Score",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("📊 Markedsstatus")
    market_condition = "bull_market"
    market_score = 8.5
    col1, col2 = st.columns([1, 3])
    with col1:
        if market_condition == "bull_market":
            st.success("📈 Bull Market")
            st.write("Markedet er i en stærk opadgående trend")
        elif market_condition == "bear_market":
            st.warning("📉 Bear Market")
            st.write("Markedet er i en nedadgående trend")
        else:
            st.info("🔄 Sideways Market")
            st.write("Markedet bevæger sig sidelæns")
    with col2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=market_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Markedsstyrke"},
            gauge={
                'axis': {'range': [0, 10]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 3], 'color': "red"},
                    {'range': [3, 6], 'color': "orange"},
                    {'range': [6, 8], 'color': "lightgreen"},
                    {'range': [8, 10], 'color': "darkgreen"}
                ]
            }
        ))
        st.plotly_chart(fig, use_container_width=True)
    st.subheader("💡 Strategianbefalinger")
    if market_condition == "bull_market":
        st.success("✅ Bull Market Anbefalinger")
        st.write("- Fokuser på vækstaktier og momentum-strategier")
        st.write("- Overvej at reducere defensive aktier")
        st.write("- Hold en lav cash-reserve")
    elif market_condition == "bear_market":
        st.warning("⚠️ Bear Market Anbefalinger")
        st.write("- Fokuser på value og defensive aktier")
        st.write("- Øg cash-reserven til 10-15%")
        st.write("- Undgå highly leveraged virksomheder")
    else:
        st.info("🔄 Sideways Market Anbefalinger")
        st.write("- Brug kombinerede GARP-strategier")
        st.write("- Fokuser på kvalitetsaktier til fair pris")
        st.write("- Hold en afbalanceret portefølje")

def main():
    initialize_app()
    config_loader = st.session_state.config_loader
    st.title("💼 Professionel Investeringsplatform")
    st.caption("Avanceret screening & værdiansættelse for alle investeringsstilarter")
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Strategi Screening", 
        "💰 Værdiansættelse",
        "📊 Portfolio Analyse",
        "🔍 Markeds Research"
    ])
    with tab1:
        strategy_screening_tab()
    with tab2:
        valuation_tab()
    with tab3:
        portfolio_analysis_tab()
    with tab4:
        market_research_tab()
    with st.sidebar:
        st.header("Platform Information")
        strategies = config_loader.get_available_strategies()
        st.subheader("Tilgængelige Strategier")
        for strategy in strategies:
            st.write(f"- {strategy.capitalize()}")
        st.subheader("Sidst Opdateret")
        st.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        st.subheader("Support")
        st.write("Email: support@investmentplatform.com")
        st.write("Version: 1.0.0")

if __name__ == "__main__":
    main()