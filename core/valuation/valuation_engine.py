# core/valuation/valuation_engine.py
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import streamlit as st
import time
from core.data.api_client import get_live_price  # ← Tilføj import øverst


# Import den nødvendige funktion
from core.data.api_client import get_fundamental_data

@dataclass
class CompanyProfile:
    """Definer virksomhedstype baseret på karakteristika"""
    ticker: str
    company_type: str  # 'startup', 'mature', 'cyclical', 'asset_heavy', 'bank'
    sector: str
    market_cap: float
    revenue_growth_5y: float
    profit_margin: float
    debt_to_equity: float
    dividend_yield: float

@dataclass
class ValuationInputs:
    """Inputdata til værdiansættelse"""
    # Finansielle nøgletal
    revenue: float
    ebitda: float
    net_income: float
    free_cash_flow: float
    book_value: float
    dividend_per_share: float
    shares_outstanding: float
    
    # Vækstantagelser
    revenue_growth_rate: float
    terminal_growth_rate: float
    
    # Risikofaktorer
    beta: float
    debt_to_equity: float
    interest_coverage: float

@dataclass
class WACCInputs:
    """Inputs til beregning af vægtede gennemsnitlige kapitalomkostninger"""
    risk_free_rate: float
    market_premium: float
    beta: float
    tax_rate: float
    debt_to_equity: float
    cost_of_debt: float

def safe_numeric(value, default=0):
    """Sikker konvertering til numerisk værdi"""
    try:
        if pd.isna(value) or value is None or value == '' or value == 'None':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

class ValuationMethodSelector:
    """Vælger bedste værdiansættelsesmetoder baseret på virksomhedstype"""
    
    METHOD_MAPPING = {
        'startup': {
            'primary': ['dcf', 'price_to_sales'],
            'secondary': ['ev_to_sales'],
            'avoid': ['pe_ratio', 'dividend_discount']
        },
        'mature': {
            'primary': ['dcf', 'pe_ratio', 'dividend_discount'],
            'secondary': ['ev_to_ebitda', 'price_to_book'],
            'avoid': []
        },
        'cyclical': {
            'primary': ['ev_to_ebitda', 'price_to_book_normalized'],
            'secondary': ['dcf_normalized'],
            'avoid': ['pe_ratio']  # Vildledende på cykliske toppe/bunde
        },
        'asset_heavy': {
            'primary': ['price_to_book', 'asset_based'],
            'secondary': ['ev_to_ebitda'],
            'avoid': ['price_to_sales']
        },
        'bank': {
            'primary': ['price_to_book', 'price_to_tangible_book'],
            'secondary': ['dividend_discount'],
            'avoid': ['ev_to_ebitda']  # EBITDA ikke relevant for banker
        }
    }
    
    @classmethod
    def get_recommended_methods(cls, company_type: str) -> Dict[str, List[str]]:
        """Returner anbefalede metoder for given virksomhedstype"""
        return cls.METHOD_MAPPING.get(company_type, cls.METHOD_MAPPING['mature'])

class WACCCalculator:
    """Beregner vægtede gennemsnitlige kapitalomkostninger"""
    
    @staticmethod
    def calculate_wacc(inputs: WACCInputs) -> Dict[str, float]:
        """
        WACC = (E/V * Re) + (D/V * Rd * (1 - Tc))
        """
        try:
            # Cost of Equity via CAPM
            cost_of_equity = inputs.risk_free_rate + inputs.beta * inputs.market_premium
            
            # Vægte - sikre vi ikke dividerer med nul
            if inputs.debt_to_equity == 0:
                debt_weight = 0
                equity_weight = 1
            else:
                debt_weight = inputs.debt_to_equity / (1 + inputs.debt_to_equity)
                equity_weight = 1 / (1 + inputs.debt_to_equity)
            
            # WACC beregning
            wacc = (equity_weight * cost_of_equity) + (debt_weight * inputs.cost_of_debt * (1 - inputs.tax_rate))
            
            return {
                'wacc': max(0.01, wacc),  # Minimum 1% WACC
                'cost_of_equity': cost_of_equity,
                'cost_of_debt': inputs.cost_of_debt,
                'debt_weight': debt_weight,
                'equity_weight': equity_weight
            }
        except Exception as e:
            st.warning(f"WACC beregning fejlede: {e}")
            return {
                'wacc': 0.10,  # Standard 10% WACC
                'cost_of_equity': 0.10,
                'cost_of_debt': 0.05,
                'debt_weight': 0.3,
                'equity_weight': 0.7
            }
class DCFValuation:
    """Discounted Cash Flow værdiansættelse"""
    
    @staticmethod
    def calculate_dcf(inputs: ValuationInputs, wacc: float, projection_years: int = 5) -> Dict[str, float]:
        """Beregner DCF værdi med terminal værdi"""
        
        try:
            # Sikkerhedstjek for inputs
            if inputs.free_cash_flow <= 0:
                # Estimer FCF fra EBITDA eller Net Income
                if inputs.ebitda > 0:
                    inputs.free_cash_flow = inputs.ebitda * 0.6  # Konservativt estimat
                elif inputs.net_income > 0:
                    inputs.free_cash_flow = inputs.net_income * 0.8
                else:
                    inputs.free_cash_flow = inputs.revenue * 0.05  # Meget konservativt
            
            # Projektér fremtidige cash flows
            projected_fcf = []
            current_fcf = inputs.free_cash_flow
            
            # Begræns vækstrate for at undgå ekstreme værdier
            growth_rate = min(inputs.revenue_growth_rate * 0.7, 0.25)  # Max 25% vækst
            
            for year in range(1, projection_years + 1):
                # Aftagende vækstrate over tid
                adjusted_growth = growth_rate * (0.80 ** (year - 1))  # Hurtigere fald
                current_fcf *= (1 + adjusted_growth)
                projected_fcf.append(max(0, current_fcf))  # Sikre positive værdier
            
            # Terminal værdi med sikkerhedstjek
            terminal_growth = min(inputs.terminal_growth_rate, 0.03)  # Max 3% terminal vækst
            if wacc <= terminal_growth:
                wacc = terminal_growth + 0.025  # Sikre at WACC > terminal vækst
            
            # ✅ TILFØJ: Sikre at WACC ikke er for tæt på terminal vækst
            if abs(wacc - terminal_growth) < 0.005:  # Hvis forskellen er < 0.5%
                wacc = terminal_growth + 0.025
            
            terminal_value = (projected_fcf[-1] * (1 + terminal_growth)) / (wacc - terminal_growth)
            
            # Diskontér til nutidsværdi
            dcf_value = 0
            for i, fcf in enumerate(projected_fcf):
                dcf_value += fcf / ((1 + wacc) ** (i + 1))
            
            # Tilføj diskonteret terminal værdi
            dcf_value += terminal_value / ((1 + wacc) ** projection_years)
            
            # Per aktie værdi med sikkerhedstjek
            if inputs.shares_outstanding <= 0:
                inputs.shares_outstanding = 1e6  # Standard værdi
            
            value_per_share = max(0, dcf_value / inputs.shares_outstanding)
            
            return {
                'enterprise_value': dcf_value,
                'terminal_value': terminal_value,
                'value_per_share': value_per_share,
                'projected_fcf': projected_fcf
            }
        
        except Exception as e:
            st.warning(f"DCF beregning fejlede: {e}")
            # Return fallback værdier
            return {
                'enterprise_value': 0,
                'terminal_value': 0,
                'value_per_share': 0,
                'projected_fcf': [0] * projection_years
            }
class ScenarioAnalysis:
    """Scenarioanalyse og stresstestning"""
    
    @staticmethod
    def create_scenarios(base_inputs: ValuationInputs) -> Dict[str, ValuationInputs]:
        """Opret best/base/worst case scenarier"""
        
        scenarios = {}
        
        # Base case (uændret)
        scenarios['base'] = base_inputs
        
        # Best case (+25% vækst, lavere risiko)
        best_inputs = ValuationInputs(**base_inputs.__dict__)
        best_inputs.revenue_growth_rate = min(0.30, best_inputs.revenue_growth_rate * 1.25)
        best_inputs.terminal_growth_rate = min(0.04, best_inputs.terminal_growth_rate * 1.15)
        best_inputs.beta = max(0.5, best_inputs.beta * 0.85)
        scenarios['best'] = best_inputs
        
        # Worst case (-30% vækst, højere risiko)
        worst_inputs = ValuationInputs(**base_inputs.__dict__)
        worst_inputs.revenue_growth_rate = max(0, worst_inputs.revenue_growth_rate * 0.70)
        worst_inputs.terminal_growth_rate = max(0.015, worst_inputs.terminal_growth_rate * 0.80)
        worst_inputs.beta = min(2.0, worst_inputs.beta * 1.30)
        scenarios['worst'] = worst_inputs
        
        return scenarios

class ComprehensiveValuation:
    """Hovedklasse der kombinerer alle værdiansættelsesmetoder"""
    
    def __init__(self, profile: CompanyProfile):
        self.profile = profile
        self.method_selector = ValuationMethodSelector()
    
    def perform_valuation(self, inputs: ValuationInputs, wacc_inputs: WACCInputs, 
                         market_price: float) -> Dict:
        """Udfør komplet værdiansættelse"""
        
        results = {
            'company_profile': self.profile,
            'recommended_methods': self.method_selector.get_recommended_methods(self.profile.company_type),
            'valuations': {},
            'scenarios': {}
        }
        
        try:
            # WACC beregning
            wacc_result = WACCCalculator.calculate_wacc(wacc_inputs)
            results['wacc'] = wacc_result
            
            # DCF værdiansættelse
            if 'dcf' in results['recommended_methods']['primary']:
                dcf_result = DCFValuation.calculate_dcf(inputs, wacc_result['wacc'])
                results['valuations']['dcf'] = dcf_result
            
            # Scenarioanalyse
            scenarios = ScenarioAnalysis.create_scenarios(inputs)
            scenario_valuations = {}
            
            for scenario_name, scenario_inputs in scenarios.items():
                try:
                    dcf_scenario = DCFValuation.calculate_dcf(scenario_inputs, wacc_result['wacc'])
                    scenario_valuations[scenario_name] = dcf_scenario['value_per_share']
                except Exception as e:
                    st.warning(f"Scenarie {scenario_name} fejlede: {e}")
                    scenario_valuations[scenario_name] = 0
            
            results['scenarios'] = scenario_valuations
            
        except Exception as e:
            st.error(f"Værdiansættelse fejlede: {e}")
            # Return fallback resultater
            results['wacc'] = {'wacc': 0.10}
            results['valuations'] = {'dcf': {'value_per_share': 0}}
            results['scenarios'] = {'best': 0, 'base': 0, 'worst': 0}
        
        return results

def determine_company_type_from_data(data):
    """Bestem virksomhedstype fra API data med bedre fejlhåndtering"""
    try:
        pe_ratio = safe_numeric(data.get('PERatio'), 15)
        dividend_yield = safe_numeric(data.get('DividendYield'), 0)
        debt_equity = safe_numeric(data.get('DebtToEquity'), 0.3)
        sector = data.get('Sector', '').lower()
        
        if 'financial' in sector or 'bank' in sector:
            return 'bank'
        elif pe_ratio > 25 and dividend_yield < 0.02:
            return 'startup'
        elif 'utilities' in sector or 'reit' in sector:
            return 'mature'
        elif 'materials' in sector or 'energy' in sector:
            return 'cyclical'
        elif debt_equity > 2:
            return 'asset_heavy'
        else:
            return 'mature'
    except Exception as e:
        st.warning(f"Fejl ved bestemmelse af virksomhedstype: {e}")
        return 'mature'

def get_valuation_data(tickers: list, max_tickers=3):
    """Henter omfattende værdiansættelsesdata for favoritter - forbedret version"""
    if not tickers:
        return pd.DataFrame()
    
    # Begræns antal for API-effektivitet
    tickers = tickers[:max_tickers]
    
    valuation_results = []
    progress_bar = st.progress(0, text="Udfører værdiansættelse...")
    
    # Standard markedsparametre
    risk_free_rate = 0.04
    market_premium = 0.06
    tax_rate = 0.22
    
    for i, ticker in enumerate(tickers):
        # ticker er defineret her - sikrer adgang i hele loopet
        st.write(f"🔍 Starter værdiansættelse for {ticker}")  # Debug
        
        try:
            # Hent fundamental data
            fundamental_data = get_fundamental_data(ticker)
            if not fundamental_data:
                st.warning(f"Ingen data fundet for {ticker}")
                continue
            
            # Hent live pris
            current_price = get_live_price(ticker)
            if current_price is None:
                current_price = 50  # Fallback hvis pris ikke kan hentes
            
            # Konverter til numeriske værdier med sikker funktion
            market_cap = safe_numeric(fundamental_data.get('MarketCapitalization'), 1e9)
            revenue = safe_numeric(fundamental_data.get('RevenueTTM'), market_cap * 0.5)
            ebitda = safe_numeric(fundamental_data.get('EBITDA'), revenue * 0.15)
            net_income = safe_numeric(fundamental_data.get('NetIncomeTTM'), revenue * 0.05)
            beta = safe_numeric(fundamental_data.get('Beta'), 1.0)
            # ✅ RETTELSE: Brug 'DebtToEquity' i stedet for 'DebtToEquityRatio'
            debt_equity = safe_numeric(fundamental_data.get('DebtToEquity'), 0.3)
            dividend_yield = safe_numeric(fundamental_data.get('DividendYield'), 0)
            shares_outstanding = safe_numeric(fundamental_data.get('SharesOutstanding'), market_cap / 50)
            book_value = safe_numeric(fundamental_data.get('BookValue'), 10)
            
            # Besteem virksomhedstype
            company_type = determine_company_type_from_data(fundamental_data)
            st.write(f"Debug: {ticker} company type = {company_type}")
            
            # Opret værdiansættelse objekter
            profile = CompanyProfile(
                ticker=ticker,
                company_type=company_type,
                sector=fundamental_data.get('Sector', 'Unknown'),
                market_cap=market_cap,
                revenue_growth_5y=0.08,  # Standard antagelse
                profit_margin=net_income/revenue if revenue > 0 else 0.05,
                debt_to_equity=debt_equity,
                dividend_yield=dividend_yield
            )
            
            # Estimer Free Cash Flow hvis manglende
            estimated_fcf = max(ebitda * 0.6, net_income * 0.8, revenue * 0.03)
            
            # Opret inputs
            inputs = ValuationInputs(
                revenue=revenue,
                ebitda=ebitda,
                net_income=net_income,
                free_cash_flow=estimated_fcf,
                book_value=book_value * shares_outstanding,
                dividend_per_share=safe_numeric(fundamental_data.get('DividendPerShare'), 0),
                shares_outstanding=shares_outstanding,
                revenue_growth_rate=min(0.25, safe_numeric(fundamental_data.get('QuarterlyRevenueGrowthYOY'), 0.08)),
                terminal_growth_rate=0.025,
                beta=max(0.5, min(2.0, beta)),  # Begræns beta
                debt_to_equity=min(5.0, debt_equity),  # Begræns gearing
                interest_coverage=8.0
            )
            
            # ✅ RETTELSE: Justér vækst efter inputs er oprettet
            if company_type == 'mature':
                inputs.revenue_growth_rate = min(0.05, inputs.revenue_growth_rate)  # Max 5%
            elif company_type == 'startup':
                inputs.revenue_growth_rate = min(0.30, inputs.revenue_growth_rate)  # Max 30%
            
            st.write(f"Debug: {ticker} revenue growth rate = {inputs.revenue_growth_rate}")
            
            wacc_inputs = WACCInputs(
                risk_free_rate=risk_free_rate,
                market_premium=market_premium,
                beta=inputs.beta,
                tax_rate=tax_rate,
                debt_to_equity=inputs.debt_to_equity,
                cost_of_debt=min(0.15, 0.03 + inputs.beta * 0.02)  # Dynamisk gældsomkostning
            )
            
            # Udfør værdiansættelse
            valuator = ComprehensiveValuation(profile)
            results = valuator.perform_valuation(inputs, wacc_inputs, current_price)
            
            # Uddrag resultater med sikkerhedstjek
            dcf_value = results.get('valuations', {}).get('dcf', {}).get('value_per_share', current_price)
            scenarios = results.get('scenarios', {})
            wacc_value = results.get('wacc', {}).get('wacc', 0.10)
            
            # Beregn upside med sikkerhedstjek
            upside_pct = 0
            if current_price > 0 and dcf_value > 0:
                upside_pct = (dcf_value - current_price) / current_price
            
            valuation_row = {
                'Ticker': ticker,
                'Current_Price': current_price,
                'Fair_Value': dcf_value,
                'Upside_Pct': upside_pct,
                'Company_Type': company_type,
                'WACC': wacc_value,
                'Best_Case': scenarios.get('best', dcf_value),
                'Base_Case': scenarios.get('base', dcf_value),
                'Worst_Case': scenarios.get('worst', dcf_value),
                'Projected_FCF': str(results.get('valuations', {}).get('dcf', {}).get('projected_fcf', [])),
                'Terminal_Growth': inputs.terminal_growth_rate,
                'Recommended_Methods': ', '.join(results.get('recommended_methods', {}).get('primary', ['DCF']))
            }
            
            valuation_results.append(valuation_row)
            st.success(f"✅ Værdiansættelse fuldført for {ticker}")
            
        except Exception as e:
            # ✅ Nu virker ticker her
            st.error(f"❌ Værdiansættelse fejlede for {ticker}: {e}")
            # Tilføj fallback række for at holde resultaterne konsistente
            valuation_results.append({
                'Ticker': ticker,
                'Current_Price': 0,
                'Fair_Value': 0,
                'Upside_Pct': 0,
                'Company_Type': 'unknown',
                'WACC': 0.10,
                'Best_Case': 0,
                'Base_Case': 0,
                'Worst_Case': 0,
                'Projected_FCF': '[]',
                'Terminal_Growth': 0.025,
                'Recommended_Methods': 'DCF'
            })
        
        # API rate limit med længere pause
        time.sleep(12)
        progress_bar.progress((i + 1) / len(tickers), text=f"Værdiansættelse: {ticker}")
    
    progress_bar.empty()
    
    if valuation_results:
        st.success(f"🎯 Værdiansættelse fuldført for {len(valuation_results)} aktier")
    
    return pd.DataFrame(valuation_results)