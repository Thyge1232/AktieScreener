# core/valuation/classifier.py

from typing import Dict, Tuple
from .wacc_calculator import CompanyType  # Korrekt import af Enum
# Importer KUN det, der er nødvendigt, fra datalaget.
# Vi fjerner 'get_fundamental_data' for at gøre klassen testbar.
from ..data.validators import AdvancedDataValidator

class IntelligentCompanyClassifier:
    """AI-like company classification based on financial characteristics"""
    CLASSIFICATION_RULES = {
        CompanyType.BANK: {
            'sector_keywords': ['financial', 'bank', 'insurance'],
            'financial_ratios': {
                'interest_income_ratio': (0.5, float('inf')),
                'loan_to_deposit': (0.3, 2.0)
            }
        },
        CompanyType.REIT: {
            'sector_keywords': ['reit', 'real estate'],
            'financial_ratios': {
                'dividend_yield': (0.03, 0.12),
                'debt_to_equity': (0.5, 3.0)
            }
        },
        CompanyType.UTILITY: {
            'sector_keywords': ['utilities', 'electric', 'gas', 'water'],
            'financial_ratios': {
                'dividend_yield': (0.025, 0.08),
                'beta': (0.3, 0.8),
                'debt_to_equity': (0.4, 1.5)
            }
        },
        CompanyType.STARTUP: {
            'financial_ratios': {
                'pe_ratio': (30, float('inf')),
                'revenue_growth': (0.20, float('inf')),
                'dividend_yield': (0, 0.02),
                'market_cap': (0, 10e9)
            }
        },
        CompanyType.GROWTH: {
            'financial_ratios': {
                'pe_ratio': (20, 50),
                'revenue_growth': (0.10, 0.30),
                'profit_margin': (0.05, 0.25),
                'dividend_yield': (0, 0.03)
            }
        },
        CompanyType.MATURE: {
            'financial_ratios': {
                'pe_ratio': (8, 25),
                'revenue_growth': (0, 0.15),
                'dividend_yield': (0.02, 0.08),
                'market_cap': (1e9, float('inf'))
            }
        },
        CompanyType.CYCLICAL: {
            'sector_keywords': ['materials', 'energy', 'industrials', 'mining'],
            'financial_ratios': {
                'beta': (1.2, 2.5),
                'debt_to_equity': (0.3, 2.0),
                'operating_margin_volatility': (0.05, float('inf'))
            }
        }
    }

    @classmethod
    def classify_company(cls, fundamental_data: Dict, sector: str = "") -> Tuple[CompanyType, float]:
        """
        Classifies a company based on a PRE-FETCHED dictionary of fundamental data.
        This method does NOT perform any I/O or API calls.
        """
        # RETTELSE: Parameteren er nu 'fundamental_data: Dict', hvilket er gyldig Python-syntaks.
        
        metrics = {
            'pe_ratio': AdvancedDataValidator.safe_numeric(fundamental_data.get('PERatio'), 15),
            'market_cap': AdvancedDataValidator.safe_numeric(fundamental_data.get('MarketCapitalization'), 1e9),
            'dividend_yield': AdvancedDataValidator.safe_numeric(fundamental_data.get('DividendYield'), 0),
            'beta': AdvancedDataValidator.safe_numeric(fundamental_data.get('Beta'), 1.0),
            'debt_to_equity': AdvancedDataValidator.safe_numeric(fundamental_data.get('DebtToEquity'), 0.5),
            'revenue_growth': AdvancedDataValidator.safe_numeric(fundamental_data.get('QuarterlyRevenueGrowthYOY'), 0.05),
            'profit_margin': AdvancedDataValidator.safe_numeric(fundamental_data.get('ProfitMargin'), 0.05),
            'operating_margin': AdvancedDataValidator.safe_numeric(fundamental_data.get('OperatingMarginTTM'), 0.08)
        }
        
        sector_lower = sector.lower()
        best_match = CompanyType.MATURE
        highest_score = 0.0
        
        for company_type, rules in cls.CLASSIFICATION_RULES.items():
            matches = 0
            total_checks = 0
            
            # Check sector keywords
            if 'sector_keywords' in rules:
                total_checks += 1
                if any(keyword in sector_lower for keyword in rules['sector_keywords']):
                    matches += 1
            
            # Check financial ratios
            if 'financial_ratios' in rules:
                num_ratio_rules = len(rules['financial_ratios'])
                total_checks += num_ratio_rules
                for ratio_name, (min_val, max_val) in rules['financial_ratios'].items():
                    metric_value = metrics.get(ratio_name)
                    if metric_value is not None and min_val <= metric_value <= max_val:
                        matches += 1
            
            # Calculate confidence as percentage of matching criteria
            confidence = matches / max(total_checks, 1)
            
            if confidence > highest_score:
                highest_score = confidence
                best_match = company_type
                
        return best_match, min(highest_score, 0.95)  # Cap confidence at 95%