# core/valuation/valuation_engine.py
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import streamlit as st

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
        # Cost of Equity via CAPM
        cost_of_equity = inputs.risk_free_rate + inputs.beta * inputs.market_premium
        
        # Vægte
        debt_weight = inputs.debt_to_equity / (1 + inputs.debt_to_equity)
        equity_weight = 1 / (1 + inputs.debt_to_equity)
        
        # WACC beregning
        wacc = (equity_weight * cost_of_equity) + (debt_weight * inputs.cost_of_debt * (1 - inputs.tax_rate))
        
        return {
            'wacc': wacc,
            'cost_of_equity': cost_of_equity,
            'cost_of_debt': inputs.cost_of_debt,
            'debt_weight': debt_weight,
            'equity_weight': equity_weight
        }

class DCFValuation:
    """Discounted Cash Flow værdiansættelse"""
    
    @staticmethod
    def calculate_dcf(inputs: ValuationInputs, wacc: float, projection_years: int = 5) -> Dict[str, float]:
        """Beregner DCF værdi med terminal værdi"""
        
        # Projektér fremtidige cash flows
        projected_fcf = []
        current_fcf = inputs.free_cash_flow
        
        for year in range(1, projection_years + 1):
            # Antag aftagende vækstrate
            growth_rate = inputs.revenue_growth_rate * (0.9 ** (year - 1))
            current_fcf *= (1 + growth_rate)
            projected_fcf.append(current_fcf)
        
        # Terminal værdi
        terminal_value = (projected_fcf[-1] * (1 + inputs.terminal_growth_rate)) / (wacc - inputs.terminal_growth_rate)
        
        # Diskontér til nutidsværdi
        dcf_value = 0
        for i, fcf in enumerate(projected_fcf):
            dcf_value += fcf / ((1 + wacc) ** (i + 1))
        
        # Tilføj diskonteret terminal værdi
        dcf_value += terminal_value / ((1 + wacc) ** projection_years)
        
        # Per aktie værdi
        value_per_share = dcf_value / inputs.shares_outstanding
        
        return {
            'enterprise_value': dcf_value,
            'terminal_value': terminal_value,
            'value_per_share': value_per_share,
            'projected_fcf': projected_fcf
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
        best_inputs.revenue_growth_rate *= 1.25
        best_inputs.terminal_growth_rate *= 1.15
        best_inputs.beta *= 0.85
        scenarios['best'] = best_inputs
        
        # Worst case (-30% vækst, højere risiko)
        worst_inputs = ValuationInputs(**base_inputs.__dict__)
        worst_inputs.revenue_growth_rate *= 0.70
        worst_inputs.terminal_growth_rate *= 0.80
        worst_inputs.beta *= 1.30
        scenarios['worst'] = worst_inputs
        
        return scenarios
    
    @staticmethod
    def stress_test_interest_rates(base_wacc_inputs: WACCInputs, rate_shocks: List[float]) -> Dict[str, float]:
        """Test påvirkning af rentestigninger"""
        stress_results = {}
        
        for shock in rate_shocks:
            stressed_inputs = WACCInputs(**base_wacc_inputs.__dict__)
            stressed_inputs.risk_free_rate += shock
            stressed_inputs.cost_of_debt += shock
            
            wacc_result = WACCCalculator.calculate_wacc(stressed_inputs)
            stress_results[f'+{shock*100:.0f}bp'] = wacc_result['wacc']
        
        return stress_results

class MultipleValuation:
    """Relativ værdiansættelse via multipler"""
    
    @staticmethod
    def calculate_multiples(inputs: ValuationInputs, market_price: float) -> Dict[str, float]:
        """Beregn vigtige multipler"""
        
        multiples = {}
        
        # P/E ratio
        if inputs.net_income > 0:
            eps = inputs.net_income / inputs.shares_outstanding
            multiples['pe_ratio'] = market_price / eps
        
        # EV/EBITDA
        enterprise_value = market_price * inputs.shares_outstanding + (inputs.debt_to_equity * market_price * inputs.shares_outstanding)
        if inputs.ebitda > 0:
            multiples['ev_ebitda'] = enterprise_value / inputs.ebitda
        
        # P/S
        if inputs.revenue > 0:
            multiples['price_to_sales'] = (market_price * inputs.shares_outstanding) / inputs.revenue
        
        # P/B
        if inputs.book_value > 0:
            book_value_per_share = inputs.book_value / inputs.shares_outstanding
            multiples['price_to_book'] = market_price / book_value_per_share
        
        return multiples
    
    @staticmethod
    def apply_peer_multiples(inputs: ValuationInputs, peer_multiples: Dict[str, float]) -> Dict[str, float]:
        """Anvend peer multipler til værdiansættelse"""
        
        valuations = {}
        
        # P/E baseret værdiansættelse
        if 'pe_ratio' in peer_multiples and inputs.net_income > 0:
            eps = inputs.net_income / inputs.shares_outstanding
            valuations['pe_valuation'] = peer_multiples['pe_ratio'] * eps
        
        # EV/EBITDA baseret værdiansættelse
        if 'ev_ebitda' in peer_multiples and inputs.ebitda > 0:
            enterprise_value = peer_multiples['ev_ebitda'] * inputs.ebitda
            equity_value = enterprise_value - (inputs.debt_to_equity * enterprise_value / (1 + inputs.debt_to_equity))
            valuations['ev_ebitda_valuation'] = equity_value / inputs.shares_outstanding
        
        return valuations

class ComprehensiveValuation:
    """Hovedklasse der kombinerer alle værdiansættelsesmetoder"""
    
    def __init__(self, profile: CompanyProfile):
        self.profile = profile
        self.method_selector = ValuationMethodSelector()
    
    def perform_valuation(self, inputs: ValuationInputs, wacc_inputs: WACCInputs, 
                         market_price: float, peer_multiples: Dict[str, float] = None) -> Dict:
        """Udfør komplet værdiansættelse"""
        
        results = {
            'company_profile': self.profile,
            'recommended_methods': self.method_selector.get_recommended_methods(self.profile.company_type),
            'valuations': {},
            'risk_analysis': {},
            'scenarios': {}
        }
        
        # WACC beregning
        wacc_result = WACCCalculator.calculate_wacc(wacc_inputs)
        results['wacc'] = wacc_result
        
        # DCF værdiansættelse
        if 'dcf' in results['recommended_methods']['primary']:
            dcf_result = DCFValuation.calculate_dcf(inputs, wacc_result['wacc'])
            results['valuations']['dcf'] = dcf_result
        
        # Multiple værdiansættelse
        current_multiples = MultipleValuation.calculate_multiples(inputs, market_price)
        results['current_multiples'] = current_multiples
        
        if peer_multiples:
            peer_valuations = MultipleValuation.apply_peer_multiples(inputs, peer_multiples)
            results['valuations']['peer_multiples'] = peer_valuations
        
        # Scenarioanalyse
        scenarios = ScenarioAnalysis.create_scenarios(inputs)
        scenario_valuations = {}
        
        for scenario_name, scenario_inputs in scenarios.items():
            dcf_scenario = DCFValuation.calculate_dcf(scenario_inputs, wacc_result['wacc'])
            scenario_valuations[scenario_name] = dcf_scenario['value_per_share']
        
        results['scenarios'] = scenario_valuations
        
        # Stress test af renter
        rate_shocks = [0.005, 0.01, 0.02]  # 50bp, 100bp, 200bp
        stress_results = ScenarioAnalysis.stress_test_interest_rates(wacc_inputs, rate_shocks)
        results['interest_rate_stress'] = stress_results
        
        return results
    
    def get_weighted_fair_value(self, valuations: Dict[str, float], 
                               probabilities: Dict[str, float] = None) -> float:
        """Beregn vægtet fair værdi baseret på scenarier"""
        
        if not probabilities:
            probabilities = {'best': 0.25, 'base': 0.50, 'worst': 0.25}
        
        weighted_value = 0
        for scenario, probability in probabilities.items():
            if scenario in valuations:
                weighted_value += valuations[scenario] * probability
        
def get_valuation_data(tickers: list, max_tickers=3):
    """Henter omfattende værdiansættelsesdata for favoritter."""
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
        try:
            # Hent fundamental data
            fundamental_data = get_fundamental_data(ticker)
            if not fundamental_data:
                continue
            
            # Konverter til numeriske værdier
            market_cap = pd.to_numeric(fundamental_data.get('MarketCapitalization', 0), errors='coerce')
            revenue = pd.to_numeric(fundamental_data.get('RevenueTTM', 0), errors='coerce')
            ebitda = pd.to_numeric(fundamental_data.get('EBITDA', 0), errors='coerce')
            net_income = pd.to_numeric(fundamental_data.get('NetIncomeTTM', 0), errors='coerce')
            beta = pd.to_numeric(fundamental_data.get('Beta', 1.0), errors='coerce')
            debt_equity = pd.to_numeric(fundamental_data.get('DebtToEquityRatio', 0.3), errors='coerce')
            dividend_yield = pd.to_numeric(fundamental_data.get('DividendYield', 0), errors='coerce')
            shares_outstanding = pd.to_numeric(fundamental_data.get('SharesOutstanding', 1), errors='coerce')
            book_value = pd.to_numeric(fundamental_data.get('BookValue', 0), errors='coerce')
            
            # Besteem virksomhedstype
            company_type = determine_company_type_from_data(fundamental_data)
            
            # Opret værdiansættelse objekter
            profile = CompanyProfile(
                ticker=ticker,
                company_type=company_type,
                sector=fundamental_data.get('Sector', 'Unknown'),
                market_cap=market_cap,
                revenue_growth_5y=0.08,  # Standard antagelse
                profit_margin=net_income/revenue if revenue > 0 else 0,
                debt_to_equity=debt_equity,
                dividend_yield=dividend_yield
            )
            
            inputs = ValuationInputs(
                revenue=revenue,
                ebitda=ebitda,
                net_income=net_income,
                free_cash_flow=ebitda * 0.7 if ebitda > 0 else 0,  # Estimat
                book_value=book_value * shares_outstanding if book_value > 0 else market_cap * 0.5,
                dividend_per_share=pd.to_numeric(fundamental_data.get('DividendPerShare', 0), errors='coerce'),
                shares_outstanding=shares_outstanding,
                revenue_growth_rate=0.08,  # Standard
                terminal_growth_rate=0.025,
                beta=beta,
                debt_to_equity=debt_equity,
                interest_coverage=8.0  # Standard
            )
            
            wacc_inputs = WACCInputs(
                risk_free_rate=risk_free_rate,
                market_premium=market_premium,
                beta=beta,
                tax_rate=tax_rate,
                debt_to_equity=debt_equity,
                cost_of_debt=0.05  # Standard
            )
            
            # Udfør værdiansættelse
            valuator = ComprehensiveValuation(profile)
            current_price = pd.to_numeric(fundamental_data.get('Price', 50), errors='coerce')
            
            results = valuator.perform_valuation(inputs, wacc_inputs, current_price)
            
            # Uddrag resultater
            dcf_value = results['valuations'].get('dcf', {}).get('value_per_share', current_price)
            scenarios = results.get('scenarios', {})
            
            valuation_row = {
                'Ticker': ticker,
                'Current_Price': current_price,
                'Fair_Value': dcf_value,
                'Upside_Pct': (dcf_value - current_price) / current_price if current_price > 0 else 0,
                'Company_Type': company_type,
                'WACC': results['wacc']['wacc'],
                'Best_Case': scenarios.get('best', dcf_value),
                'Base_Case': scenarios.get('base', dcf_value),
                'Worst_Case': scenarios.get('worst', dcf_value),
                'Projected_FCF': str(results['valuations'].get('dcf', {}).get('projected_fcf', [])),
                'Terminal_Growth': inputs.terminal_growth_rate,
                'Recommended_Methods': ', '.join(results['recommended_methods']['primary'])
            }
            
            valuation_results.append(valuation_row)
            
        except Exception as e:
            st.warning(f"Værdiansættelse fejlede for {ticker}: {e}")
        
        time.sleep(12)  # API rate limit
        progress_bar.progress((i + 1) / len(tickers), text=f"Værdiansættelse: {ticker}")
    
    progress_bar.empty()
    return pd.DataFrame(valuation_results)

def determine_company_type_from_data(data):
    """Bestem virksomhedstype fra API data"""
    try:
        pe_ratio = pd.to_numeric(data.get('PERatio', 15), errors='coerce')
        dividend_yield = pd.to_numeric(data.get('DividendYield', 0), errors='coerce')
        debt_equity = pd.to_numeric(data.get('DebtToEquityRatio', 0.3), errors='coerce')
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
    except:
        return 'mature'