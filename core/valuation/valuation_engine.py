# core/valuation/valuation_engine.py (opdateret med ValuationConfig)
"""Hovedmotor for omfattende værdiansættelse."""

import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Importer de nye moduler og konfiguration
from core.valuation.valuation_config import ValuationConfig
from .classifier import IntelligentCompanyClassifier
# Importer fra de opdaterede filer
from .wacc_calculator import WACCCalculator, WACCInputs, CompanyProfile, CompanyType
from .dcf_engine import DCFEngine, ValuationInputs
from .comparable_valuation import ComparableValuation
from .risk_assessment import RiskAssessment # Antager denne eksisterer og er opdateret
# Brug safe_numeric fra api_client via AdvancedDataValidator
from ..data.client import get_fundamental_data, get_live_price, APIResponse, AdvancedDataValidator

logger = logging.getLogger(__name__)

# Enums og klasser er nu i separate filer, så de importeres ovenfor
# Hvis IntelligentCompanyClassifier stadig er her, bør den måske flyttes til risk_assessment.py

class ComprehensiveValuationEngine:
    """Main valuation engine orchestrating all methods"""

    def __init__(self, config: ValuationConfig = None):
        # Brug de nye moduler
        self.dcf_calculator = DCFEngine()
        self.comparable_calculator = ComparableValuation()
        self.risk_assessor = RiskAssessment()
        self.wacc_calculator = WACCCalculator()
        # Gem konfigurationen
        self.config = config or ValuationConfig() # Brug den givne config eller opret standard

    def _create_valuation_inputs(self, data: Dict, profile: CompanyProfile) -> ValuationInputs:
        """Create comprehensive valuation inputs from fundamental data using config"""
        # Brug safe_numeric fra api_client via AdvancedDataValidator
        # Basic financials
        revenue = AdvancedDataValidator.safe_numeric(data.get('RevenueTTM'), 1e9)
        ebitda = AdvancedDataValidator.safe_numeric(data.get('EBITDA'), revenue * self.config.fallback_ebitda_margin)
        net_income = AdvancedDataValidator.safe_numeric(data.get('NetIncomeTTM'), revenue * 0.05)
        book_value = AdvancedDataValidator.safe_numeric(data.get('BookValue'), 10) * AdvancedDataValidator.safe_numeric(data.get('SharesOutstanding'), 1e6)
        dividend_per_share = AdvancedDataValidator.safe_numeric(data.get('DividendPerShare'), 0)
        shares_outstanding = AdvancedDataValidator.safe_numeric(data.get('SharesOutstanding'), 1e6)

        # Growth and profitability
        revenue_growth_rate = AdvancedDataValidator.safe_numeric(data.get('QuarterlyRevenueGrowthYOY'), 0.05)
        # Estimate EBITDA growth (could be refined with more data)
        ebitda_growth_rate = revenue_growth_rate * 0.9 # Simplified assumption
        # Brug config for terminal growth cap
        terminal_growth_rate = min(0.025, self.config.terminal_growth_cap) # Default terminal growth, capped by config
        operating_margin = AdvancedDataValidator.safe_numeric(data.get('OperatingMarginTTM'), 0.08)
        # Brug config for default tax rate
        tax_rate = self.config.default_tax_rate # Default tax rate from config

        # Balance sheet
        total_debt = AdvancedDataValidator.safe_numeric(data.get('TotalDebt'), revenue * self.config.fallback_debt_to_revenue)
        cash_and_equivalents = AdvancedDataValidator.safe_numeric(data.get('CashAndCashEquivalents'), total_debt * self.config.fallback_cash_to_debt)
        working_capital = AdvancedDataValidator.safe_numeric(data.get('WorkingCapital'), revenue * 0.1) # Estimate if missing
        capex = AdvancedDataValidator.safe_numeric(data.get('CapitalExpenditures'), revenue * 0.05) # Estimate if missing

        # Risk metrics
        beta = profile.beta
        debt_to_equity = profile.debt_to_equity
        # Estimate interest coverage (EBITDA / Interest Expense)
        # We don't have interest expense, so we estimate it
        estimated_interest_expense = total_debt * 0.05 # Assume 5% average interest rate
        interest_coverage = ebitda / max(estimated_interest_expense, 1)

        # Industry benchmarks (could be fetched from a separate source or config)
        # Brug config-værdier
        industry_pe = self.config.comparable_pe_default
        industry_ev_ebitda = self.config.comparable_ev_ebitda_default
        industry_growth_rate = self.config.comparable_growth_threshold_high # eller en anden relevant værdi

        return ValuationInputs(
            revenue=revenue,
            ebitda=ebitda,
            net_income=net_income,
            free_cash_flow=AdvancedDataValidator.safe_numeric(data.get('OperatingCashflowTTM'), net_income * 0.7) - capex,
            book_value=book_value,
            dividend_per_share=dividend_per_share,
            shares_outstanding=shares_outstanding,
            revenue_growth_rate=revenue_growth_rate,
            ebitda_growth_rate=ebitda_growth_rate,
            terminal_growth_rate=terminal_growth_rate,
            operating_margin=operating_margin,
            tax_rate=tax_rate,
            total_debt=total_debt,
            cash_and_equivalents=cash_and_equivalents,
            working_capital=working_capital,
            capex=capex,
            beta=beta,
            debt_to_equity=debt_to_equity,
            interest_coverage=interest_coverage,
            industry_pe=industry_pe,
            industry_ev_ebitda=industry_ev_ebitda,
            industry_growth_rate=industry_growth_rate
        )

    def _create_wacc_inputs(self, profile: CompanyProfile, inputs: ValuationInputs) -> WACCInputs:
        """Create WACC inputs using config"""
        # Brug config-værdier
        risk_free_rate = self.config.risk_free_rate  # Risk-free rate from config
        market_premium = self.config.market_premium   # Market risk premium from config
        cost_of_debt = 0.05     # 5% cost of debt (could be estimated or come from config)
        # Enhanced factors (kan også komme fra config)
        size_premium = 0.0  # Could be based on market cap
        country_risk_premium = 0.0  # For international companies
        liquidity_premium = 0.0  # Could be based on trading volume
        return WACCInputs(
            risk_free_rate=risk_free_rate,
            market_premium=market_premium,
            beta=inputs.beta,
            tax_rate=inputs.tax_rate, # Brug tax rate fra inputs (kan komme fra config)
            debt_to_equity=inputs.debt_to_equity,
            cost_of_debt=cost_of_debt,
            size_premium=size_premium,
            country_risk_premium=country_risk_premium,
            liquidity_premium=liquidity_premium
        )

    def _get_valuation_weights(self, company_type: CompanyType) -> Dict[str, float]:
        """Get method weights based on company type using config"""
        # Brug vægtninger fra config
        weights = self.config.valuation_weights
        # Håndtér CompanyType enum nøgler
        type_key = company_type.value # Brug .value for at matche string-nøgler i config
        if type_key in weights:
            return weights[type_key]
        else:
            # Fallback til default
            return weights.get('default', weights.get('mature', {})) # Default to mature eller en anden fallback

    def _calculate_weighted_fair_value(self, method_values: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate weighted average fair value"""
        total_weighted_value = 0
        total_weight = 0
        for method, value in method_values.items():
            weight = weights.get(method, 0)
            if value > 0: # Only include positive valuations
                total_weighted_value += value * weight
                total_weight += weight
        if total_weight > 0:
            return total_weighted_value / total_weight
        else:
            # Fallback if all methods failed
            valid_values = [v for v in method_values.values() if v > 0]
            return sum(valid_values) / len(valid_values) if valid_values else 0

    def perform_comprehensive_valuation(
        self,
        ticker: str,
        market_price: float = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Perform complete valuation analysis
        Args:
            ticker: Stock ticker symbol
            market_price: Current market price (optional, will be fetched if not provided)
            progress_callback: Optional callback function to report progress (e.g., for UI)
        """
        if progress_callback:
            progress_callback(f"Starting comprehensive valuation for {ticker}")
        else:
            # Fallback to logging if no callback provided
            logger.info(f"Starting comprehensive valuation for {ticker}")

        try:
            # Get fundamental data
            if progress_callback: progress_callback("Fetching fundamental data...")
            fundamental_response = get_fundamental_data(ticker)
            if not fundamental_response.success or not fundamental_response.data:
                return {'error': f'No fundamental data available for {ticker}'}

            data = fundamental_response.data

            # Get current price if not provided
            if market_price is None:
                if progress_callback: progress_callback("Fetching live price...")
                price_response = get_live_price(ticker)
                market_price = price_response.data.get('price') if price_response.success else 50.0

            # Create company profile
            if progress_callback: progress_callback("Classifying company...")
            company_type, classification_confidence = IntelligentCompanyClassifier.classify_company(
                data, data.get('Sector', '')
            )
            # Brug safe_numeric fra api_client via AdvancedDataValidator
            profile = CompanyProfile(
                ticker=ticker,
                company_type=company_type,
                sector=data.get('Sector', 'Unknown'),
                industry=data.get('Industry', 'Unknown'),
                market_cap=AdvancedDataValidator.safe_numeric(data.get('MarketCapitalization'), 1e9),
                revenue_growth_5y=AdvancedDataValidator.safe_numeric(data.get('QuarterlyRevenueGrowthYOY'), 0.05),
                profit_margin=AdvancedDataValidator.safe_numeric(data.get('ProfitMargin'), 0.05),
                debt_to_equity=AdvancedDataValidator.safe_numeric(data.get('DebtToEquity'), 0.5),
                dividend_yield=AdvancedDataValidator.safe_numeric(data.get('DividendYield'), 0.0),
                beta=AdvancedDataValidator.safe_numeric(data.get('Beta'), 1.0)
            )

            # Create valuation inputs
            if progress_callback: progress_callback("Preparing valuation inputs...")
            inputs = self._create_valuation_inputs(data, profile)

            # Calculate WACC
            if progress_callback: progress_callback("Calculating WACC...")
            wacc_inputs = self._create_wacc_inputs(profile, inputs)
            wacc_result = self.wacc_calculator.calculate_comprehensive_wacc(wacc_inputs, profile)

            # Perform DCF valuation - Brug config og korrekt signatur
            if progress_callback: progress_callback("Running DCF valuation...")
            dcf_result = self.dcf_calculator.calculate_comprehensive_dcf(
                inputs, wacc_result, self.config.dcf_projection_years_default,self.config
            )

            # Comparable valuations - Brug config
            if progress_callback: progress_callback("Running comparable valuations...")
            pe_valuation = self.comparable_calculator.calculate_pe_valuation(
            inputs, self.config.comparable_pe_default
            )
            ev_ebitda_valuation = self.comparable_calculator.calculate_ev_ebitda_valuation(
            inputs, self.config.comparable_ev_ebitda_default
            )
            pb_valuation = self.comparable_calculator.calculate_price_to_book(
            inputs, self.config.comparable_pb_default
            )

            # Risk assessment
            if progress_callback: progress_callback("Assessing risks...")
            risk_assessment = self.risk_assessor.assess_company_risk(inputs, profile)

            # Aggregate results with weighting based on company type
            valuation_weights = self._get_valuation_weights(company_type)
            weighted_fair_value = self._calculate_weighted_fair_value(
                {
                    'dcf': dcf_result['value_per_share'],
                    'pe': pe_valuation['fair_value'],
                    'ev_ebitda': ev_ebitda_valuation['fair_value'],
                    'pb': pb_valuation['fair_value']
                },
                valuation_weights
            )

            # Calculate upside/downside
            upside_potential = (weighted_fair_value - market_price) / market_price if market_price > 0 else 0

            if progress_callback: progress_callback("Valuation complete!")
            return {
                'ticker': ticker,
                'current_price': market_price,
                'fair_value_weighted': weighted_fair_value,
                'upside_potential': upside_potential,
                'company_profile': profile,
                'classification_confidence': classification_confidence,
                'valuation_methods': {
                    'dcf': dcf_result,
                    'pe_comparable': pe_valuation,
                    'ev_ebitda_comparable': ev_ebitda_valuation,
                    'price_to_book': pb_valuation
                },
                'method_weights': valuation_weights,
                'wacc_analysis': wacc_result,
                'risk_assessment': risk_assessment,
                'financial_inputs': inputs,
                'data_quality': {
                    'source': fundamental_response.source.value,
                    'confidence': fundamental_response.confidence.value,
                    'cache_hit': fundamental_response.cache_hit
                }
            }
        except Exception as e:
            logger.error(f"Comprehensive valuation failed for {ticker}: {e}", exc_info=True)
            return {
                'error': f'Valuation failed: {str(e)}',
                'ticker': ticker,
                'current_price': market_price or 0
            }

# Global instance for easy access - Brug standard config
valuation_engine = ComprehensiveValuationEngine()

# Funktion til at hente data til favorites - Brug standard config
def get_valuation_data(tickers: List[str]) -> pd.DataFrame:
    """
    Henter værdiansættelsesdata for en liste af tickers.
    Args:
        tickers: Liste af aktiesymboler (f.eks. ['AAPL', 'MSFT']).
    Returns:
        En pandas DataFrame med værdiansættelsesresultater for hver ticker.
    """
    # Brug standard config
    engine = ComprehensiveValuationEngine() 
    results = []
    for ticker in tickers:
        try:
            logger.info(f"Starter værdiansættelse for {ticker}")
            # Kald hovedmetoden i motoren
            result = engine.perform_comprehensive_valuation(ticker)
            # Tjek om resultatet er succesfuldt
            if result and 'error' not in result:
                # Udtræk og formatér de data, som favorites.py forventer
                processed_result = {
                    'Ticker': result.get('ticker'),
                    'Current_Price': result.get('current_price'),
                    'Fair_Value': result.get('fair_value_weighted'),
                    'Upside_Pct': result.get('upside_potential'),
                    # Tilføj flere felter efter behov. Disse er eksempler:
                    'Company_Type': result.get('company_profile', {}).get('company_type', {}).get('value') if result.get('company_profile') and result['company_profile'].get('company_type') else 'Unknown',
                    'WACC': result.get('wacc_analysis', {}).get('wacc'),
                    # Hvis du har data fra DCF-modellen:
                    # 'Terminal_Growth': result.get('valuation_methods', {}).get('dcf', {}).get('assumptions', {}).get('terminal_growth'),
                    # 'Projected_FCF': str(result.get('valuation_methods', {}).get('dcf', {}).get('projected_fcf', [])), # Konverter liste til string
                    # Tilføj Risk Assessment data hvis nødvendigt
                    # ...
                }
                results.append(processed_result)
            else:
                # Håndtér fejl for en enkelt ticker
                error_msg = result.get('error', 'Ukendt fejl')
                logger.warning(f"Værdiansættelse fejlede for {ticker}: {error_msg}")
                # Du kan vælge at inkludere en fejl-række eller bare springe over
                # Her inkluderer vi en række med fejlinfo
                results.append({
                    'Ticker': ticker,
                    'Error': error_msg
                    # Andre kolonner vil være NaN/None
                })
        except Exception as e:
            # Håndtér uventede fejl
            logger.error(f"Uventet fejl ved værdiansættelse af {ticker}: {e}", exc_info=True)
            results.append({
                'Ticker': ticker,
                'Error': f"Uventet fejl: {str(e)}"
            })
    # Returnér en DataFrame. favorites.py forventer, at denne ikke er tom, hvis der ikke er fejl.
    return pd.DataFrame(results)