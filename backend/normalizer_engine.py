import re

class NormalizerEngine:
    def __init__(self):
        pass

    def normalize(self, lang_data: dict, category: str, subcategory: str, rule_type: str, token: str) -> str:
        """
        Normalize the matched token based on its rule_type and language data mappings.
        """
        try:
            subcat_data = lang_data.get("categories", {}).get(category, {}).get("subcategories", {}).get(subcategory, {})
            if not subcat_data:
                return token

            if rule_type == "digit_by_digit":
                return self._normalize_digit_by_digit(token, subcat_data)
            elif rule_type == "cardinal":
                return self._normalize_cardinal(token, subcat_data)
            elif rule_type == "currency":
                return self._normalize_currency(token, subcat_data)
            elif rule_type in ["unit_with_plural", "length_unit", "weight_unit", "speed_unit", "area_unit", "volume_unit", "time_unit"]:
                return self._normalize_unit(token, subcat_data)
            elif rule_type == "spell_out":
                return " ".join(list(token))
            elif rule_type == "time":
                return self._normalize_time(token, subcat_data)
            elif rule_type == "date":
                return token  # Complex format, return as is for MVP or implement simple version
            else:
                return token
        except Exception as e:
            print(f"Normalization error: {e}")
            return token

    def _normalize_digit_by_digit(self, token: str, subcat_data: dict) -> str:
        pron_map = subcat_data.get("pronunciation_map", {})
        if not pron_map:
            return " ".join(list(token))
        return " ".join([pron_map.get(char, char) for char in token])

    def _normalize_cardinal(self, token: str, subcat_data: dict) -> str:
        scale_words = subcat_data.get("scale_words", {})
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

    def _normalize_currency(self, token: str, subcat_data: dict) -> str:
        currency_map = subcat_data.get("currency_map", {})
        # Extract number
        num_match = re.search(r'[0-9]+(\.[0-9]+)?', token)
        if not num_match:
            return token
        num = num_match.group(0)
        
        for sym, word in currency_map.items():
            if sym in token:
                return f"{num} {word}"
        
        return token

    def _normalize_unit(self, token: str, subcat_data: dict) -> str:
        unit_map = subcat_data.get("unit_map", {})
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

    def _normalize_time(self, token: str, subcat_data: dict) -> str:
        time_words = subcat_data.get("time_words", {})
        res = token
        for k, v in time_words.items():
            res = res.replace(k, v)
        return res
