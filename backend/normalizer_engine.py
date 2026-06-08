import re

class NormalizerEngine:
    def __init__(self):
        pass

    def normalize(self, lang_data: dict, category: str, subcategory: str, rule_type: str, token: str) -> str:
        """
        Normalize the matched token based on its rule_type and language data mappings.
        """
        try:
            if rule_type == "digit_by_digit":
                return self._normalize_digit_by_digit(token, lang_data)
            elif rule_type == "cardinal":
                return self._normalize_cardinal(token, lang_data)
            elif rule_type == "currency":
                return self._normalize_currency(token, lang_data)
            elif rule_type in ["unit_with_plural", "length_unit", "weight_unit", "speed_unit", "area_unit", "volume_unit", "time_unit"]:
                return self._normalize_unit(token, lang_data)
            elif rule_type == "spell_out":
                return " ".join(list(token))
            elif rule_type == "time":
                return self._normalize_time(token, lang_data)
            elif rule_type == "date":
                return token  # Complex format, return as is for MVP or implement simple version
            else:
                return token
        except Exception as e:
            print(f"Normalization error: {e}")
            return token

    def _normalize_digit_by_digit(self, token: str, lang_data: dict) -> str:
        pron_map = lang_data.get("mappings", {}).get("digits", {})
        if not pron_map:
            return " ".join(list(token))
        return " ".join([pron_map.get(char, char) for char in token])

    def _normalize_cardinal(self, token: str, lang_data: dict) -> str:
        scale_words = lang_data.get("mappings", {}).get("cardinal", {}).get("scale_words", {})
        if not scale_words:
            return token
        
        # Simple implementation for < 100000 just for MVP demo
        try:
            num = int(re.sub(r'[^0-9]', '', token))
            if num in [int(k) for k in scale_words.keys()]:
                return scale_words[str(num)]
            # If not a direct match, just return token (full cardinal spelling is complex)
            return str(num)
        except:
            return token

    def _normalize_currency(self, token: str, lang_data: dict) -> str:
        currency_map = lang_data.get("mappings", {}).get("currency", {})
        # Extract number
        num_match = re.search(r'[0-9]+(\.[0-9]+)?', token)
        if not num_match:
            return token
        num = num_match.group(0)
        
        for sym, word in currency_map.items():
            if sym in token:
                return f"{num} {word}"
        
        return token

    def _normalize_unit(self, token: str, lang_data: dict) -> str:
        unit_map = lang_data.get("mappings", {}).get("unit", {})
        num_match = re.search(r'[0-9]+(\.[0-9]+)?', token)
        if not num_match:
            return token
        num = num_match.group(0)
        
        for sym, words in unit_map.items():
            if re.search(rf'\b{sym}\b', token, re.IGNORECASE):
                word = words.get("plural", sym) if float(num) != 1 else words.get("singular", sym)
                if isinstance(words, str):
                    word = words
                return f"{num} {word}"
        
        return token

    def _normalize_time(self, token: str, lang_data: dict) -> str:
        time_words = lang_data.get("mappings", {}).get("time", {})
        res = token
        for k, v in time_words.items():
            res = res.replace(k, v)
        return res
