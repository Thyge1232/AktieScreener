# Corrected WACC Calculator - Fixes the CAPM implementation

import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

@dataclass
class WACCInputs:
    # Market data
    market_cap: float
    total_debt: float
    cash: float
    risk_free_rate: float
    market_return: float
    beta: float
    tax_rate: float
    cost_of_debt: Optional[float] = None
    
    # Additional risk premiums (optional - use either input OR calculated, not both)
    size_premium_override: Optional[float] = None  # Renamed to clarify it's an override
    country_risk_premium: float = 0.0
    company_specific_premium: float = 0.0  # For additional company-specific risks

@dataclass
class WACCResults:
    wacc: float
    cost_of_equity: float
    cost_of_debt: float
    weight_equity: float
    weight_debt: float
    market_risk_premium: float
    size_premium: float
    country_risk_premium: float
    company_specific_premium: float
    total_risk_adjustments: float
    net_debt: float
    enterprise_value: float

class CorrectedWACCCalculator:
    """
    Corrected WACC Calculator with proper CAPM implementation.
    
    The correct CAPM formula with additional risk premiums is:
    Cost of Equity = Risk-Free Rate + (Beta × Market Risk Premium) + Size Premium + Country Risk Premium + Other Adjustments
    
    Key corrections:
    1. Size and country risk premiums are added AFTER beta multiplication, not included in market premium
    2. Use either input size premium OR calculated size premium, not both
    3. All additional premiums are separate additive components
    """
    
    @staticmethod
    def _calculate_market_risk_premium(market_return: float, risk_free_rate: float) -> float:
        """Calculate the pure market risk premium without other adjustments."""
        return market_return - risk_free_rate
    
    @staticmethod
    def _calculate_size_premium(market_cap: float) -> float:
        """
        Calculate size premium based on market capitalization.
        
        Typical size premium ranges:
        - Large cap (>$10B): 0-0.5%
        - Mid cap ($2B-$10B): 0.5-1.5%
        - Small cap ($300M-$2B): 1.5-3%
        - Micro cap (<$300M): 3-6%
        """
        market_cap_millions = market_cap / 1_000_000
        
        if market_cap_millions >= 10_000:  # Large cap
            return 0.002  # 0.2%
        elif market_cap_millions >= 2_000:  # Mid cap
            return 0.01   # 1.0%
        elif market_cap_millions >= 300:   # Small cap
            return 0.025  # 2.5%
        else:  # Micro cap
            return 0.045  # 4.5%
    
    @staticmethod
    def _estimate_cost_of_debt(risk_free_rate: float, credit_spread: float = 0.02) -> float:
        """Estimate cost of debt if not provided."""
        return risk_free_rate + credit_spread
    
    @staticmethod
    def calculate_wacc(inputs: WACCInputs) -> WACCResults:
        """
        Calculate WACC with corrected CAPM implementation.
        
        Corrected formula:
        Cost of Equity = RF + (Beta × MRP) + Size Premium + Country Risk Premium + Company Specific Premium
        
        Where:
        - RF = Risk-free rate
        - MRP = Market Risk Premium (Market Return - Risk-free rate)
        - Additional premiums are additive, not multiplicative with beta
        """
        
        # 1. Calculate pure market risk premium (without other adjustments)
        market_risk_premium = CorrectedWACCCalculator._calculate_market_risk_premium(
            inputs.market_return, inputs.risk_free_rate
        )
        
        # 2. Determine size premium (use override if provided, otherwise calculate)
        if inputs.size_premium_override is not None:
            size_premium = inputs.size_premium_override
            logger.info(f"Using override size premium: {size_premium:.3f}")
        else:
            size_premium = CorrectedWACCCalculator._calculate_size_premium(inputs.market_cap)
            logger.info(f"Calculated size premium from market cap: {size_premium:.3f}")
        
        # 3. Calculate cost of equity using corrected CAPM formula
        # CORRECTED: Additional premiums are added AFTER beta multiplication
        capm_base = inputs.risk_free_rate + (inputs.beta * market_risk_premium)
        risk_adjustments = size_premium + inputs.country_risk_premium + inputs.company_specific_premium
        cost_of_equity = capm_base + risk_adjustments
        
        logger.info(f"CAPM breakdown:")
        logger.info(f"  Risk-free rate: {inputs.risk_free_rate:.3f}")
        logger.info(f"  Beta × Market Risk Premium: {inputs.beta:.2f} × {market_risk_premium:.3f} = {inputs.beta * market_risk_premium:.3f}")
        logger.info(f"  Size premium: {size_premium:.3f}")
        logger.info(f"  Country risk premium: {inputs.country_risk_premium:.3f}")
        logger.info(f"  Company specific premium: {inputs.company_specific_premium:.3f}")
        logger.info(f"  Total cost of equity: {cost_of_equity:.3f}")
        
        # 4. Calculate cost of debt
        cost_of_debt = inputs.cost_of_debt or CorrectedWACCCalculator._estimate_cost_of_debt(inputs.risk_free_rate)
        after_tax_cost_of_debt = cost_of_debt * (1 - inputs.tax_rate)
        
        # 5. Calculate net debt and enterprise value
        net_debt = inputs.total_debt - inputs.cash
        enterprise_value = inputs.market_cap + net_debt
        
        # 6. Calculate weights
        weight_equity = inputs.market_cap / enterprise_value
        weight_debt = net_debt / enterprise_value
        
        # Handle negative net debt (more cash than debt)
        if net_debt < 0:
            weight_debt = 0
            weight_equity = 1
            logger.warning("Negative net debt - using 100% equity weighting")
        
        # 7. Calculate WACC
        wacc = (weight_equity * cost_of_equity) + (weight_debt * after_tax_cost_of_debt)
        
        return WACCResults(
            wacc=wacc,
            cost_of_equity=cost_of_equity,
            cost_of_debt=after_tax_cost_of_debt,
            weight_equity=weight_equity,
            weight_debt=weight_debt,
            market_risk_premium=market_risk_premium,
            size_premium=size_premium,
            country_risk_premium=inputs.country_risk_premium,
            company_specific_premium=inputs.company_specific_premium,
            total_risk_adjustments=risk_adjustments,
            net_debt=net_debt,
            enterprise_value=enterprise_value
        )

def display_wacc_analysis(results: WACCResults, inputs: WACCInputs):
    """Display comprehensive WACC analysis."""
    
    st.subheader("📊 WACC Analysis Results")
    
    # Main WACC result
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("WACC", f"{results.wacc:.2%}", help="Weighted Average Cost of Capital")
    with col2:
        st.metric("Cost of Equity", f"{results.cost_of_equity:.2%}")
    with col3:
        st.metric("After-Tax Cost of Debt", f"{results.cost_of_debt:.2%}")
    
    # Capital structure
    st.subheader("🏗️ Capital Structure")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Equity Weight", f"{results.weight_equity:.1%}")
    with col2:
        st.metric("Debt Weight", f"{results.weight_debt:.1%}")
    with col3:
        st.metric("Enterprise Value", f"${results.enterprise_value:,.0f}")
    
    # CAPM breakdown
    st.subheader("📈 Cost of Equity Breakdown (Corrected CAPM)")
    
    breakdown_data = {
        'Component': [
            'Risk-Free Rate',
            'Beta × Market Risk Premium',
            '├─ Beta',
            '├─ Market Risk Premium',
            'Size Premium',
            'Country Risk Premium',
            'Company Specific Premium',
            'Total Cost of Equity'
        ],
        'Value': [
            f"{inputs.risk_free_rate:.2%}",
            f"{inputs.beta * results.market_risk_premium:.2%}",
            f"{inputs.beta:.2f}",
            f"{results.market_risk_premium:.2%}",
            f"{results.size_premium:.2%}",
            f"{results.country_risk_premium:.2%}",
            f"{results.company_specific_premium:.2%}",
            f"{results.cost_of_equity:.2%}"
        ],
        'Formula Component': [
            'RF',
            'β × (RM - RF)',
            'β',
            '(RM - RF)',
            'Size Premium',
            'Country Risk',
            'Company Risk',
            'RF + β×(RM-RF) + Adjustments'
        ]
    }
    
    df_breakdown = pd.DataFrame(breakdown_data)
    st.dataframe(df_breakdown, use_container_width=True, hide_index=True)
    
    # Formula explanation
    with st.expander("📚 Corrected CAMP Formula Explanation"):
        st.markdown("""
        **Corrected Cost of Equity Formula:**
        ```
        Cost of Equity = RF + (β × MRP) + Size Premium + Country Risk Premium + Other Adjustments
        ```
        
        **Key Corrections Made:**
        1. **Size and Country Risk Premiums**: Added AFTER beta multiplication, not included in market premium
        2. **No Double Counting**: Use either input size premium OR calculated size premium, not both
        3. **Additive Structure**: Additional premiums are separate additive components
        
        **Components:**
        - **RF**: Risk-free rate (base return for risk-free investment)
        - **β**: Beta (systematic risk relative to market)
        - **MRP**: Market Risk Premium (RM - RF, pure market excess return)
        - **Size Premium**: Additional return required for smaller companies
        - **Country Risk Premium**: Additional return for country-specific risks
        - **Company Specific Premium**: Additional return for company-specific risks
        """)
    
    # Sensitivity analysis
    if st.checkbox("Show Sensitivity Analysis"):
        st.subheader("🎯 WACC Sensitivity Analysis")
        
        # Beta sensitivity
        beta_range = [inputs.beta * 0.8, inputs.beta * 0.9, inputs.beta, inputs.beta * 1.1, inputs.beta * 1.2]
        wacc_sensitivity = []
        
        for beta in beta_range:
            test_inputs = WACCInputs(
                market_cap=inputs.market_cap,
                total_debt=inputs.total_debt,
                cash=inputs.cash,
                risk_free_rate=inputs.risk_free_rate,
                market_return=inputs.market_return,
                beta=beta,
                tax_rate=inputs.tax_rate,
                cost_of_debt=inputs.cost_of_debt,
                size_premium_override=inputs.size_premium_override,
                country_risk_premium=inputs.country_risk_premium,
                company_specific_premium=inputs.company_specific_premium
            )
            test_results = CorrectedWACCCalculator.calculate_wacc(test_inputs)
            wacc_sensitivity.append(test_results.wacc)
        
        sensitivity_df = pd.DataFrame({
            'Beta': beta_range,
            'WACC': [f"{w:.2%}" for w in wacc_sensitivity]
        })
        st.dataframe(sensitivity_df, use_container_width=True, hide_index=True)

# Example usage function
def run_wacc_calculator():
    """Streamlit interface for WACC calculator."""
    
    st.title("🧮 Corrected WACC Calculator")
    st.markdown("**Fixed implementation with proper CAPM formula**")
    
    with st.form("wacc_inputs"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Company Financials")
            market_cap = st.number_input("Market Cap ($)", value=10_000_000_000.0, step=1_000_000_000.0)
            total_debt = st.number_input("Total Debt ($)", value=5_000_000_000.0, step=100_000_000.0)
            cash = st.number_input("Cash ($)", value=1_000_000_000.0, step=100_000_000.0)
            tax_rate = st.number_input("Tax Rate", value=0.25, min_value=0.0, max_value=1.0, step=0.01)
            cost_of_debt = st.number_input("Cost of Debt (optional)", value=0.04, min_value=0.0, max_value=1.0, step=0.001, help="Leave as default for estimation")
        
        with col2:
            st.subheader("Market Parameters")
            risk_free_rate = st.number_input("Risk-Free Rate", value=0.04, min_value=0.0, max_value=1.0, step=0.001)
            market_return = st.number_input("Market Return", value=0.10, min_value=0.0, max_value=1.0, step=0.001)
            beta = st.number_input("Beta", value=1.2, min_value=0.0, max_value=5.0, step=0.1)
            
            st.subheader("Risk Adjustments")
            size_premium_override = st.number_input("Size Premium Override (optional)", value=0.0, min_value=0.0, max_value=0.2, step=0.001, help="Leave as 0 to auto-calculate")
            country_risk_premium = st.number_input("Country Risk Premium", value=0.0, min_value=0.0, max_value=0.2, step=0.001)
            company_specific_premium = st.number_input("Company Specific Premium", value=0.0, min_value=0.0, max_value=0.2, step=0.001)
        
        calculate_button = st.form_submit_button("Calculate WACC")
    
    if calculate_button:
        inputs = WACCInputs(
            market_cap=market_cap,
            total_debt=total_debt,
            cash=cash,
            risk_free_rate=risk_free_rate,
            market_return=market_return,
            beta=beta,
            tax_rate=tax_rate,
            cost_of_debt=cost_of_debt if cost_of_debt > 0 else None,
            size_premium_override=size_premium_override if size_premium_override > 0 else None,
            country_risk_premium=country_risk_premium,
            company_specific_premium=company_specific_premium
        )
        
        try:
            results = CorrectedWACCCalculator.calculate_wacc(inputs)
            display_wacc_analysis(results, inputs)
            
        except Exception as e:
            st.error(f"Error calculating WACC: {str(e)}")
            logger.error(f"WACC calculation error: {e}")

if __name__ == "__main__":
    run_wacc_calculator()