from typing import Dict, Any, List
import pandas as pd
import numpy as np

def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """Beregner Compound Annual Growth Rate (CAGR)"""
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return 0.0
    return (end_value / start_value) ** (1 / years) - 1

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """Beregner Sharpe Ratio for en række afkast"""
    if len(returns) < 2:
        return 0.0
    
    excess_returns = [r - (risk_free_rate / len(returns)) for r in returns]
    mean_excess = np.mean(excess_returns)
    std_excess = np.std(excess_returns, ddof=1)
    
    if std_excess == 0:
        return 0.0
    
    return mean_excess / std_excess * np.sqrt(len(returns))

def calculate_beta(asset_returns: List[float], market_returns: List[float]) -> float:
    """Beregner beta for en aktie i forhold til markedet"""
    if len(asset_returns) != len(market_returns) or len(asset_returns) < 2:
        return 0.0
    
    covariance = np.cov(asset_returns, market_returns)[0, 1]
    market_variance = np.var(market_returns)
    
    if market_variance == 0:
        return 0.0
    
    return covariance / market_variance

def calculate_working_capital(current_assets: float, current_liabilities: float) -> float:
    """Beregner omløbsmidler"""
    return current_assets - current_liabilities

def calculate_debt_to_equity(total_debt: float, total_equity: float) -> float:
    """Beregner gæld-til-egenkapital forhold"""
    if total_equity == 0:
        return float('inf')
    return total_debt / total_equity

def calculate_interest_coverage(ebit: float, interest_expense: float) -> float:
    """Beregner rentedækningsgrad"""
    if interest_expense == 0:
        return float('inf')
    return ebit / interest_expense

def calculate_roe(net_income: float, shareholder_equity: float) -> float:
    """Beregner Return on Equity (ROE)"""
    if shareholder_equity == 0:
        return 0.0
    return net_income / shareholder_equity

def calculate_roa(net_income: float, total_assets: float) -> float:
    """Beregner Return on Assets (ROA)"""
    if total_assets == 0:
        return 0.0
    return net_income / total_assets

def calculate_gross_margin(revenue: float, cost_of_goods_sold: float) -> float:
    """Beregner bruttomargen"""
    if revenue == 0:
        return 0.0
    return (revenue - cost_of_goods_sold) / revenue

def calculate_current_ratio(current_assets: float, current_liabilities: float) -> float:
    """Beregner likviditetsgrad"""
    if current_liabilities == 0:
        return float('inf')
    return current_assets / current_liabilities

def calculate_quick_ratio(current_assets: float, inventory: float, current_liabilities: float) -> float:
    """Beregner acid-test"""
    if current_liabilities == 0:
        return float('inf')
    return (current_assets - inventory) / current_liabilities

def calculate_piotroski_score(metrics: Dict[str, Any]) -> int:
    """Beregner Piotroski F-Score baseret på finansielle metrikker"""
    score = 0
    
    # Profitabilitet
    if metrics.get("net_income", 0) > 0:
        score += 1
    if metrics.get("roe", 0) > 0:
        score += 1
    if metrics.get("operating_cash_flow", 0) > 0:
        score += 1
    if metrics.get("operating_cash_flow", 0) > metrics.get("net_income", 0):
        score += 1
    
    # Finansiel styrke
    if metrics.get("long_term_debt", 0) < metrics.get("long_term_debt_prev", float('inf')):
        score += 1
    if metrics.get("current_ratio", 0) > metrics.get("current_ratio_prev", 0):
        score += 1
    if metrics.get("share_issuance", 0) <= 0:  # Ingen nye aktier udstedt
        score += 1
    if metrics.get("gross_margin", 0) > metrics.get("gross_margin_prev", 0):
        score += 1
    
    # Operations effektivitet
    if metrics.get("asset_turnover", 0) > metrics.get("asset_turnover_prev", 0):
        score += 1
    
    return score