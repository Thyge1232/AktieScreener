import pandas as pd
import io
from typing import Dict, List, Any

class ReportGenerator:
    """Genererer rapporter og eksportformater"""
    
    def generate_screening_report(self, results: List[Dict[str, Any]], profile: Dict[str, Any]) -> io.BytesIO:
        """Genererer en screening rapport i Excel-format"""
        # Konverter resultater til DataFrame
        df = pd.DataFrame(results)
        
        # Formater kolonner
        if "multibagger_score" in df.columns:
            df = df.sort_values("multibagger_score", ascending=False)
            df = df.rename(columns={
                "multibagger_score": "Kvalitets Score"
            })
        elif "value_score" in df.columns:
            df = df.sort_values("value_score", ascending=False)
            df = df.rename(columns={
                "value_score": "Value Score"
            })
        elif "deep_value_score" in df.columns:
            df = df.sort_values("deep_value_score", ascending=False)
            df = df.rename(columns={
                "deep_value_score": "Deep Value Score"
            })
        
        # Forbered Excel-fil
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Hovedresultater
            df.to_excel(writer, sheet_name='Resultater', index=False)
            
            # Sammendrag
            summary_data = {
                "Antal aktier fundet": [len(df)],
                "Profil": [profile["name"]],
                "Strategitype": [profile.get("strategy_type", "multibagger")]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Sammendrag', index=False)
        
        return output
    
    def generate_valuation_report(self, valuation_results: Dict[str, Any], 
                                metrics: Dict[str, Any], ticker: str) -> io.BytesIO:
        """Genererer en værdiansættelsesrapport i Excel-format"""
        # Forbered Excel-fil
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Værdiansættelsesresultater
            valuation_df = pd.DataFrame([valuation_results])
            valuation_df.to_excel(writer, sheet_name='Værdiansættelse', index=False)
            
            # Grundlæggende metrikker
            metrics_df = pd.DataFrame([{
                "Ticker": ticker,
                "Navn": metrics.get("name", "N/A"),
                "Sektor": metrics.get("sector", "N/A"),
                "Markedsværdi": metrics.get("market_cap", "N/A"),
                "Aktuel pris": metrics.get("current_price", "N/A")
            }])
            metrics_df.to_excel(writer, sheet_name='Grundlæggende Data', index=False)
            
            # Parametre
            params = valuation_results.get("assumptions", {})
            params_df = pd.DataFrame(list(params.items()), columns=['Parameter', 'Værdi'])
            params_df.to_excel(writer, sheet_name='Parametre', index=False)
        
        return output
    
    def generate_portfolio_analysis(self, portfolios: Dict[str, List[Dict[str, Any]]]) -> io.BytesIO:
        """Genererer en porteføljeanalyse rapport"""
        # Forbered Excel-fil
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for portfolio_name, portfolio in portfolios.items():
                # Konverter til DataFrame
                df = pd.DataFrame(portfolio)
                
                # Beregn porteføljemæssige metrikker
                if "weight" not in df.columns:
                    df["weight"] = 1 / len(df)
                
                # Gem i Excel
                df.to_excel(writer, sheet_name=portfolio_name[:31], index=False)
        
        return output