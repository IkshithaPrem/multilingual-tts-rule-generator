"""
Language Resource Loader for TTS Text Normalization Framework
Loads and caches language JSON resource files.
"""

import os
import json
from typing import Dict, List, Optional


class LanguageLoader:
    """Loads language resource files from the resources/languages directory."""

    def __init__(self, resources_dir: Optional[str] = None):
        if resources_dir is None:
            # Default: relative to this file's directory
            resources_dir = os.path.join(os.path.dirname(__file__), "resources", "languages")
        self.resources_dir = resources_dir
        self._cache: Dict[str, Dict] = {}

    def get_available_languages(self) -> List[Dict]:
        """Return list of available languages with code and name."""
        languages = []
        if not os.path.exists(self.resources_dir):
            return languages
        for fname in sorted(os.listdir(self.resources_dir)):
            if fname.endswith(".json"):
                lang_code = fname[:-5]
                try:
                    data = self.load_language(lang_code)
                    languages.append({
                        "code": data.get("language", lang_code),
                        "name": data.get("language_name", lang_code.upper())
                    })
                except Exception:
                    pass
        return languages

    def load_language(self, lang_code: str) -> Dict:
        """Load a language resource file by language code."""
        if lang_code in self._cache:
            return self._cache[lang_code]

        fpath = os.path.join(self.resources_dir, f"{lang_code}.json")
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"Language resource file not found: {fpath}")

        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._cache[lang_code] = data
        return data

    def get_categories_for_language(self, lang_code: str) -> List[Dict]:
        """Return list of categories and subcategories for a language."""
        data = self.load_language(lang_code)
        result = []
        for cat_name, cat_data in data.get("categories", {}).items():
            subcats = list(cat_data.get("subcategories", {}).keys())
            result.append({
                "category": cat_name,
                "subcategories": subcats
            })
        return result