import os
import time
import requests
import warnings
from typing import Dict, Any, Tuple, Optional

class PricingManager:
    """
    Manages LLM model pricing by fetching from a remote JSON file with TTL caching.
<<<<<<< HEAD
=======
    
    Priority:
    1. Remote JSON (if URL provided and fetch succeeds)
    2. Fallback to Langfuse (returns 0.0 costs, allowing Langfuse server to calculate)
    3. Safe default
>>>>>>> 2f99cf588aa2ae714f120625cd9b8f6a59f265b5
    """
    
    DEFAULT_URL = "https://raw.githubusercontent.com/sudarshan-zuneko/dynamic-pricing-json/main/pricing.json"
    
    def __init__(self, url: Optional[str] = None, ttl: int = 600):
        self.url = url or os.getenv("PRICING_JSON_URL", self.DEFAULT_URL)
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, float]] = {}
        self._version: str = "initial"
        self._last_fetch: float = 0
<<<<<<< HEAD
        self._fetch_timeout = 2.0

    def _fetch_remote(self) -> None:
=======
        self._fetch_timeout = 2.0  # seconds

    def _fetch_remote(self) -> None:
        """Fetch pricing from remote URL and update cache."""
>>>>>>> 2f99cf588aa2ae714f120625cd9b8f6a59f265b5
        try:
            response = requests.get(self.url, timeout=self._fetch_timeout)
            response.raise_for_status()
            data = response.json()
<<<<<<< HEAD
=======
            
>>>>>>> 2f99cf588aa2ae714f120625cd9b8f6a59f265b5
            if "models" in data:
                self._cache = data["models"]
                self._version = data.get("version", str(int(time.time())))
                self._last_fetch = time.time()
        except Exception as e:
<<<<<<< HEAD
            warnings.warn(f"langfuse-custom-tracer: Failed to fetch remote pricing from {self.url} - {e}")

    def _refresh_if_needed(self) -> None:
=======
            # Fail silently to avoid breaking the LLM call path
            warnings.warn(f"langfuse-custom-tracer: Failed to fetch remote pricing from {self.url} - {e}")

    def _refresh_if_needed(self) -> None:
        """Refresh cache if TTL has expired."""
>>>>>>> 2f99cf588aa2ae714f120625cd9b8f6a59f265b5
        if time.time() - self._last_fetch > self.ttl:
            self._fetch_remote()

    def get_price(self, model: str) -> Tuple[Dict[str, float], str, str]:
<<<<<<< HEAD
        self._refresh_if_needed()
        model_lower = model.lower()
        if model_lower in self._cache:
            return self._cache[model_lower], self._version, "json"
        
=======
        """
        Get pricing for a model.
        
        Returns:
            (price_dict, version, source)
        """
        self._refresh_if_needed()
        
        model_lower = model.lower()
        
        # 1. Try exact match in cache
        if model_lower in self._cache:
            return self._cache[model_lower], self._version, "json"
            
        # 2. Try partial match (startswith)
        # Sort keys by length descending to match most specific model first
>>>>>>> 2f99cf588aa2ae714f120625cd9b8f6a59f265b5
        sorted_keys = sorted(self._cache.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if model_lower.startswith(key.lower()):
                return self._cache[key], self._version, "json"
                
<<<<<<< HEAD
        return {"input": 0.0, "output": 0.0, "cached": 0.0}, "langfuse-native", "langfuse"

pricing_manager = PricingManager()

def get_pricing_manager():
    return pricing_manager
=======
        # 3. Fallback to Langfuse (send 0 cost, let server handle it)
        # If model is unknown, returning 0 cost allows Langfuse to use its own pricing directory
        return {"input": 0.0, "output": 0.0, "cached": 0.0}, "langfuse-native", "langfuse"

# Singleton instance
pricing_manager = PricingManager()
>>>>>>> 2f99cf588aa2ae714f120625cd9b8f6a59f265b5
