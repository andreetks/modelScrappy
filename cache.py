import json
import os
import hashlib
from datetime import datetime

class ScraperCache:
    """
    Simple file-based cache mechanism.
    """
    def __init__(self, cache_dir="cache_data"):
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_hash(self, key):
        return hashlib.md5(key.encode()).hexdigest()

    def get(self, url):
        """Retrieve data from cache if exists."""
        key_hash = self._get_hash(url)
        file_path = os.path.join(self.cache_dir, f"{key_hash}.json")
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"✅ Cache hit for {url[:30]}...")
                    return data
            except:
                return None
        return None

    def save(self, url, data):
        """Save data to cache."""
        key_hash = self._get_hash(url)
        file_path = os.path.join(self.cache_dir, f"{key_hash}.json")
        
        # Add timestamp
        data["cached_at"] = datetime.now().isoformat()
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Data cached for {url[:30]}...")
