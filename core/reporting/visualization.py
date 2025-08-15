import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any

class Visualization:
    """Genererer avancerede visualiseringer for investeringsdata"""
    
    def strategy_comparison_chart(self, results: Dict[str, List[Dict[str, Any]]]) -> go.Figure:
        """Genererer en sammenligningsgraf for forskellige strategier"""
        # Forbered data
        data = []
        for strategy, result_list in results.items():
            for result in result_list:
                score_key = self._get_score_key(result)
                if score_key in result:
                    data.append({
                        "Strategi": strategy,
                        "Aktie": result.get("ticker", "N/A"),
                        "Score": result[score_key],
                        "Sektor": result.get("sector", "Ukendt")
                    })
        
        if not data:
            return go.Figure()
        
        df = pd.DataFrame(data)
        
        # Opret graf
        fig = px.scatter(
            df, 
            x="Score", 
            y="Aktie", 
            color="Sektor",
            hover_data=["Sektor"],
            title="Strategi Sammenligning",
            labels={"Score": "Kvalitets Score", "Aktie": "Ticker"}
        )
        
        fig.update_layout(
            xaxis_title="Score",
            yaxis_title="Aktie",
            showlegend=True
        )
        
        return fig
    
    def _get_score_key(self, result: Dict[str, Any]) -> str:
        """Finder den relevante score-nøgle i resultaterne"""
        if "multibagger_score" in result:
            return "multibagger_score"
        elif "value_score" in result:
            return "value_score"
        elif "deep_value_score" in result:
            return "deep_value_score"
        elif "combined_score" in result:
            return "combined_score"
        return "score"
    
    def valuation_gauge(self, margin_of_safety: float) -> go.Figure:
        """Genererer en gauge-visning af margin of safety"""
        # Fastlæg farve baseret på margin of safety
        if margin_of_safety > 0.3:
            color = "darkgreen"
        elif margin_of_safety > 0.15:
            color = "lightgreen"
        elif margin_of_safety > 0:
            color = "orange"
        else:
            color = "red"
        
        # Opret gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=margin_of_safety,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Margin of Safety"},
            gauge={
                'axis': {'range': [-1, 1]},
                'bar': {'color': color},
                'steps': [
                    {'range': [-1, -0.2], 'color': "red"},
                    {'range': [-0.2, 0], 'color': "orange"},
                    {'range': [0, 0.2], 'color': "lightgreen"},
                    {'range': [0.2, 1], 'color': "darkgreen"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': margin_of_safety
                }
            }
        ))
        
        fig.update_layout(
            height=300
        )
        
        return fig
    
    def sector_distribution_chart(self, results: List[Dict[str, Any]]) -> go.Figure:
        """Genererer en sektordistributionsgraf"""
        # Tæl aktier pr. sektor
        sector_counts = {}
        for result in results:
            sector = result.get("sector", "Ukendt")
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        # Opret dataframe
        df = pd.DataFrame({
            "Sektor": list(sector_counts.keys()),
            "Antal aktier": list(sector_counts.values())
        })
        
        # Opret graf
        fig = px.pie(
            df, 
            values="Antal aktier", 
            names="Sektor",
            title="Sektordistribution"
        )
        
        return fig
    
    def historical_performance_chart(self, ticker: str, history: pd.DataFrame) -> go.Figure:
        """Genererer en historisk performance graf"""
        fig = go.Figure()
        
        # Tilføj pris
        fig.add_trace(go.Scatter(
            x=history.index, 
            y=history['Close'],
            mode='lines',
            name='Pris'
        ))
        
        # Tilføj 50-dages SMA
        if len(history) >= 50:
            history['SMA50'] = history['Close'].rolling(50).mean()
            fig.add_trace(go.Scatter(
                x=history.index, 
                y=history['SMA50'],
                mode='lines',
                name='50-dages SMA',
                line=dict(dash='dash')
            ))
        
        # Tilføj 200-dages SMA
        if len(history) >= 200:
            history['SMA200'] = history['Close'].rolling(200).mean()
            fig.add_trace(go.Scatter(
                x=history.index, 
                y=history['SMA200'],
                mode='lines',
                name='200-dages SMA',
                line=dict(dash='dash')
            ))
        
        fig.update_layout(
            title=f'Historisk Performance - {ticker}',
            xaxis_title='Dato',
            yaxis_title='Pris',
            hovermode="x unified"
        )
        
        return fig
    
    def score_distribution_chart(self, results: List[Dict[str, Any]]) -> go.Figure:
        """Genererer en scorefordelingsgraf"""
        # Find alle scores
        scores = []
        for result in results:
            score_key = self._get_score_key(result)
            if score_key in result:
                scores.append(result[score_key])
        
        if not scores:
            return go.Figure()
        
        # Opret histogram
        fig = px.histogram(
            x=scores,
            nbins=20,
            labels={'x': 'Score', 'y': 'Antal aktier'},
            title='Score Fordeling'
        )
        
        fig.update_layout(
            xaxis_title='Score',
            yaxis_title='Antal aktier'
        )
        
        return fig