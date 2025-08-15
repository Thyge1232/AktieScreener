from typing import Dict, List, Any

class UniversalScreener:
    """Fælles screening engine for alle investeringsstrategier"""
    
    def __init__(self, data_fetcher):
        self.data_fetcher = data_fetcher
        self.strategy_screener = {
            "multibagger": self._screen_multibagger,
            "value": self._screen_value,
            "deep_value": self._screen_deep_value,
            "combined": self._screen_combined
        }
    
    def screen(self, tickers: List[str], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Udfører screening baseret på profilens strategy_type"""
        strategy_type = profile.get("strategy_type", "multibagger")
        
        if strategy_type not in self.strategy_screener:
            raise ValueError(f"Ukendt strategitype: {strategy_type}")
        
        return self.strategy_screener[strategy_type](tickers, profile)
    
    def _screen_multibagger(self, tickers: List[str], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Multibagger-specifik screening logik"""
        from .multibagger_screener import MultibaggerScreener
        return MultibaggerScreener(self.data_fetcher).screen(tickers, profile)
    
    def _screen_value(self, tickers: List[str], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Value-specifik screening logik"""
        from .value_screener import ValueScreener
        return ValueScreener(self.data_fetcher).screen(tickers, profile)
    
    def _screen_deep_value(self, tickers: List[str], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Deep value-specifik screening logik"""
        from .deep_value_screener import DeepValueScreener
        return DeepValueScreener(self.data_fetcher).screen(tickers, profile)
    
    def _screen_combined(self, tickers: List[str], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Kombineret screening logik"""
        # For kombinerede profiler, udfør screening med underliggende strategier
        if "weighting" not in profile:
            raise ValueError("Kombineret profil mangler weighting parameter")
        
        # Identificer underliggende strategier
        growth_score_weight = profile["weighting"].get("growth_score", 0)
        value_score_weight = profile["weighting"].get("value_score", 0)
        deep_value_score_weight = profile["weighting"].get("deep_value_score", 0)
        
        results = []
        for ticker in tickers:
            # Hent alle metrikker
            metrics = self.data_fetcher.fetch_all_metrics(ticker)
            if not metrics:
                continue
            
            # Beregn scores for relevante strategier
            total_score = 0
            score_components = {}
            
            if growth_score_weight > 0:
                from .multibagger_screener import MultibaggerScreener
                growth_score = MultibaggerScreener(self.data_fetcher)._calculate_score(metrics, profile)
                total_score += growth_score * growth_score_weight
                score_components["growth_score"] = growth_score
            
            if value_score_weight > 0:
                from .value_screener import ValueScreener
                value_score = ValueScreener(self.data_fetcher)._calculate_score(metrics, profile)
                total_score += value_score * value_score_weight
                score_components["value_score"] = value_score
            
            if deep_value_score_weight > 0:
                from .deep_value_screener import DeepValueScreener
                deep_value_score = DeepValueScreener(self.data_fetcher)._calculate_score(metrics, profile)
                total_score += deep_value_score * deep_value_score_weight
                score_components["deep_value_score"] = deep_value_score
            
            # Tjek om aktien opfylder grundlæggende kriterier
            if self._passes_basic_filters(metrics, profile["parameters"]):
                metrics["combined_score"] = total_score
                metrics["score_components"] = score_components
                results.append(metrics)
        
        # Sorter efter combined score
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results
    
    def _passes_basic_filters(self, metrics: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Tjekker om aktien opfylder grundlæggende kriterier for en kombineret profil"""
        # Markedsværdi
        market_cap = metrics.get("market_cap", 0)
        if not (params["min_market_cap"] <= market_cap <= params["max_market_cap"]):
            return False
        
        return True
    
    def calculate_strategy_score(self, metrics: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """Beregner en strategispecifik score"""
        strategy_type = profile.get("strategy_type", "multibagger")
        
        if strategy_type == "multibagger":
            from .multibagger_screener import MultibaggerScreener
            return MultibaggerScreener(self.data_fetcher)._calculate_score(metrics, profile)
        elif strategy_type == "value":
            from .value_screener import ValueScreener
            return ValueScreener(self.data_fetcher)._calculate_score(metrics, profile)
        elif strategy_type == "deep_value":
            from .deep_value_screener import DeepValueScreener
            return DeepValueScreener(self.data_fetcher)._calculate_score(metrics, profile)
        elif strategy_type == "combined":
            # For kombinerede profiler, brug allerede beregnet score
            return metrics.get("combined_score", 0)
        else:
            return 0