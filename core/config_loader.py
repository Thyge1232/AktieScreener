import json
import os
from typing import Dict, Any, List

class ConfigLoader:
    """Central konfigurationshåndtering for hele platformen"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.strategy_dir = os.path.join(config_dir, "strategies")
        self.valuation_dir = os.path.join(config_dir, "valuation")
        
        # Opret standardkonfigurationer hvis de ikke eksisterer
        self._ensure_default_configs()
    
    def _ensure_default_configs(self):
        """Opret standardkonfigurationer hvis de ikke eksisterer"""
        # Strategikonfigurationer
        strategy_files = [
            "multibagger_profiles.json",
            "value_profiles.json",
            "deep_value_profiles.json",
            "combined_profiles.json"
        ]
        
        for file in strategy_files:
            path = os.path.join(self.strategy_dir, file)
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                # Her ville vi normalt indsætte standardkonfigurationen
                # For nu, bare opret en tom fil
                with open(path, 'w') as f:
                    json.dump({"global": {}, "profiles": {}}, f, indent=2)
        
        # Værdiansættelseskonfigurationer
        valuation_files = [
            "valuation_models.json",
            "strategy_specific_params.json"
        ]
        
        for file in valuation_files:
            path = os.path.join(self.valuation_dir, file)
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                # Her ville vi normalt indsætte standardkonfigurationen
                with open(path, 'w') as f:
                    json.dump({}, f, indent=2)
    
    def load_strategy_profiles(self, strategy_type: str) -> Dict[str, Any]:
        """Indlæser profiler for en specifik strategitype"""
        filename = f"{strategy_type}_profiles.json"
        path = os.path.join(self.strategy_dir, filename)
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Konfigurationsfil ikke fundet: {path}")
        
        with open(path, 'r') as f:
            config = json.load(f)
        
        # Valider konfigurationen
        self._validate_strategy_config(config, strategy_type)
        
        return config
    
    def load_valuation_models(self) -> Dict[str, Any]:
        """Indlæser alle værdiansættelsesmodeller"""
        path = os.path.join(self.valuation_dir, "valuation_models.json")
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Konfigurationsfil ikke fundet: {path}")
        
        with open(path, 'r') as f:
            models = json.load(f)
        
        return models
    
    def load_strategy_specific_params(self) -> Dict[str, Any]:
        """Indlæser strategispecifikke parametre for værdiansættelse"""
        path = os.path.join(self.valuation_dir, "strategy_specific_params.json")
        
        if not os.path.exists(path):
            return {}
        
        with open(path, 'r') as f:
            params = json.load(f)
        
        return params
    
    def _validate_strategy_config(self, config: Dict[str, Any], strategy_type: str):
        """Validerer at konfigurationen har den korrekte struktur"""
        if "global" not in config or "profiles" not in config:
            raise ValueError(f"Ugyldig konfigurationsstruktur for {strategy_type}")
        
        for profile_name, profile in config["profiles"].items():
            if "strategy_type" not in profile:
                profile["strategy_type"] = strategy_type
            
            if profile["strategy_type"] != strategy_type:
                raise ValueError(
                    f"Profil {profile_name} har forkert strategitype: "
                    f"{profile['strategy_type']} (forventede {strategy_type})"
                )
            
            if "parameters" not in profile:
                raise ValueError(f"Profil {profile_name} mangler parameters")
    
    def save_strategy_profiles(self, strategy_type: str, config: Dict[str, Any]):
        """Gemmer profiler for en specifik strategitype"""
        filename = f"{strategy_type}_profiles.json"
        path = os.path.join(self.strategy_dir, filename)
        
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def get_available_strategies(self) -> List[str]:
        """Returnerer en liste over tilgængelige strategityper"""
        strategies = []
        for file in os.listdir(self.strategy_dir):
            if file.endswith("_profiles.json"):
                strategy = file.replace("_profiles.json", "")
                strategies.append(strategy)
        return strategies