from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class UniversalScreener:
    """
    En centraliseret screening-motor, der fungerer som en dispatcher.
    Den delegerer den specifikke logik for filtrering og score-beregning
    til de relevante, strategi-specifikke screener-klasser.
    """
    
    def __init__(self, data_fetcher: Any):
        """
        Initialiserer screeneren med en data_fetcher.
        
        Args:
            data_fetcher: Et objekt, der kan hente finansielle data (f.eks. UniversalDataFetcher).
        """
        self.data_fetcher = data_fetcher
        # Cache til strategy screeners for at undgå at oprette dem hver gang
        self._strategy_screeners = {}
    
    def _get_strategy_screener(self, strategy_type: str):
        """Henter eller opretter en strategy screener"""
        if strategy_type not in self._strategy_screeners:
            if strategy_type == "multibagger":
                from .multibagger_screener import MultibaggerScreener
                self._strategy_screeners[strategy_type] = MultibaggerScreener(self.data_fetcher)
            elif strategy_type == "value":
                from .value_screener import ValueScreener
                self._strategy_screeners[strategy_type] = ValueScreener(self.data_fetcher)
            elif strategy_type == "deep_value":
                from .deep_value_screener import DeepValueScreener
                self._strategy_screeners[strategy_type] = DeepValueScreener(self.data_fetcher)
            else:
                logger.warning(f"Ukendt strategitype: {strategy_type}")
                return None
        
        return self._strategy_screeners.get(strategy_type)
    
    def calculate_strategy_score(self, metrics: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """
        Delegerer score-beregning til den korrekte strategi-specifikke screener.
        """
        strategy_type = profile.get("strategy_type", "multibagger")
        
        if strategy_type == "combined":
            # For kombinerede profiler kan scoren være beregnet på forhånd
            return metrics.get("combined_score", 0)
        
        # Hent strategy screener
        screener = self._get_strategy_screener(strategy_type)
        if screener:
            # Kald den private _calculate_score metode som findes i MultibaggerScreener
            return screener._calculate_score(metrics, profile)
        else:
            logger.warning(f"Kunne ikke finde screener for strategitype '{strategy_type}'")
            return 0.0
    
    def _passes_filters(self, metrics: Dict[str, Any], parameters: Dict[str, Any]) -> bool:
        """
        Denne metode er til bagudkompatibilitet med den eksisterende app.py kode
        der kalder st.session_state.screener._passes_filters direkte.
        """
        # Dette er en fallback - vi kan ikke vide hvilken strategi der skal bruges
        # så vi prøver multibagger som default
        return self.passes_filters_for_profile(metrics, {
            "strategy_type": "multibagger",
            "parameters": parameters
        })
    
    def passes_filters_for_profile(self, metrics: Dict[str, Any], profile: Dict[str, Any]) -> bool:
        """
        Tjekker, om en akties metrikker opfylder kriterierne for en given profil,
        ved at delegere til den korrekte strategi-specifikke screener.
        """
        strategy_type = profile.get("strategy_type", "multibagger")
        parameters = profile.get("parameters", {})
        
        if not parameters:
            logger.warning("Ingen parametre fundet i profil")
            return False
        
        if strategy_type == "combined":
            # Implementer basic filter for kombinerede strategier
            return self._combined_filter(metrics, parameters)
        
        # Hent strategy screener
        screener = self._get_strategy_screener(strategy_type)
        if screener:
            # Kald den private _passes_filters metode
            return screener._passes_filters(metrics, parameters)
        else:
            logger.warning(f"Kunne ikke finde screener for strategitype '{strategy_type}'")
            return False
    
    def _combined_filter(self, metrics: Dict[str, Any], parameters: Dict[str, Any]) -> bool:
        """Basic filter for kombinerede strategier"""
        # Markedsværdi check
        market_cap = metrics.get("market_cap", 0)
        if market_cap == 0:
            return False
        
        min_cap = parameters.get("min_market_cap", 0)
        max_cap = parameters.get("max_market_cap", float('inf'))
        
        if not (min_cap <= market_cap <= max_cap):
            return False
        
        # Basis kvalitetschecks
        roe = metrics.get("roe")
        if roe is not None:
            min_roe = parameters.get("min_roe", -999)  # Meget lav default
            if roe < min_roe:
                return False
        
        # Revenue growth check hvis det findes
        revenue_growth = metrics.get("revenue_growth")
        if revenue_growth is not None:
            min_rev_growth = parameters.get("min_revenue_growth", -999)
            if revenue_growth < min_rev_growth:
                return False
        
        return True
    
    def screen_with_profile(self, tickers: List[str], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Kører en komplet screening med en specifik profil
        """
        strategy_type = profile.get("strategy_type", "multibagger")
        results = []
        
        # Hvis det er en specifik strategi, brug den direkte
        if strategy_type in ["multibagger", "value", "deep_value"]:
            screener = self._get_strategy_screener(strategy_type)
            if screener and hasattr(screener, 'screen'):
                return screener.screen(tickers, profile)
        
        # Fallback: manual screening
        for ticker in tickers:
            try:
                metrics = self.data_fetcher.fetch_all_metrics(ticker, strategy_type)
                if not metrics:
                    continue
                    
                if self.passes_filters_for_profile(metrics, profile):
                    # Beregn score
                    metrics["score"] = self.calculate_strategy_score(metrics, profile)
                    results.append(metrics)
                    
            except Exception as e:
                logger.warning(f"Fejl ved screening af {ticker}: {e}")
                continue
        
        # Sorter efter score
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results