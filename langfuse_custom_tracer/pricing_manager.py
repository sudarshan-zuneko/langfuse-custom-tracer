import os
import time
import requests
import warnings
from typing import Dict, Any, Tuple, Optional

class PricingManager:
    """
    Manages LLM model pricing by fetching from a remote JSON file with TTL caching.
    """
    
    DEFAULT_URL = "https://raw.githubusercontent.com/sudarshan-zuneko/dynamic-pricing-json/main/pricing.json"
    
    def __init__(self, url: Optional[str] = None, ttl: int = 600):
        self.url = url or os.getenv("PRICING_JSON_URL", self.DEFAULT_URL)
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, float]] = {}
        self._version: str = "initial"
        self._last_fetch: float = 0
        self._fetch_timeout = 2.0

    def _fetch_remote(self) -> None:
        try:
            response = requests.get(self.url, timeout=self._fetch_timeout)
            response.raise_for_status()
            data = response.json()
            if "models" in data:
                self._cache = data["models"]
                self._version = data.get("version", str(int(time.time())))
                self._last_fetch = time.time()
        except Exception as e:
            warnings.warn(f"langfuse-custom-tracer: Failed to fetch remote pricing from {self.url} - {e}")

    def _refresh_if_needed(self) -> None:
        if time.time() - self._last_fetch > self.ttl:
            self._fetch_remote()

    def get_price(self, model: str) -> Tuple[Dict[str, float], str, str]:
        self._refresh_if_needed()
        model_lower = model.lower()
        if model_lower in self._cache:
            return self._cache[model_lower], self._version, "json"
        
        sorted_keys = sorted(self._cache.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if model_lower.startswith(key.lower()):
                return self._cache[key], self._version, "json"
                
        return {"input": 0.0, "output": 0.0, "cached": 0.0}, "langfuse-native", "langfuse"

pricing_manager = PricingManager()

def get_pricing_manager():
    return pricing_manager
