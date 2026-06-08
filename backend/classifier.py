"""
Lightweight ML/Context-Aware Category Classifier for TTS Text Normalization
Detects categories from raw text using pattern matching + contextual signals.
"""

import re
from typing import Dict, List, Tuple, Optional


class CategoryClassifier:
    """
    Lightweight context-aware classifier that detects TTS normalization categories.
    Uses a combination of:
    1. Regex pattern matching
    2. Contextual keyword analysis
    3. Position-of-speech heuristics
    4. Score-based ranking for ambiguous cases
    """

    def __init__(self):
        # Context keywords that disambiguate categories
        self.context_keywords = {
            "PINCODE": {
                "positive": ["pin", "pincode", "zip", "postal", "post", "code",
                             "area", "district", "zipcode"],
                "negative": ["rank", "score", "number", "roll", "id", "year", "floor", "room"]
            },
            "NUMBER_cardinal": {
                "positive": ["rank", "score", "number", "roll", "floor", "room",
                             "house", "age", "count", "total", "price", "value",
                             "page", "chapter", "version", "id"],
                "negative": ["pin", "pincode", "zip", "postal", "phone", "mobile", "tel"]
            },
            "NUMBER_phone": {
                "positive": ["call", "phone", "mobile", "contact", "number", "tel",
                             "reach", "dial", "whatsapp"],
                "negative": ["pin", "zip", "postal", "rank", "score"]
            },
            "DATE": {
                "positive": ["date", "on", "born", "birthday", "anniversary",
                             "scheduled", "meeting", "event", "deadline", "today",
                             "yesterday", "tomorrow", "since", "until", "from", "by"],
                "negative": []
            },
            "TIME": {
                "positive": ["at", "time", "hours", "clock", "sharp", "around",
                             "approximately", "meet", "call", "scheduled"],
                "negative": []
            },
            "UNIT_size": {
                "positive": ["tall", "long", "wide", "high", "deep", "measures",
                             "height", "width", "length", "size", "distance", "far"],
                "negative": []
            },
            "UNIT_weight": {
                "positive": ["weighs", "weight", "heavy", "light", "mass"],
                "negative": []
            },
            "UNIT_speed": {
                "positive": ["speed", "fast", "slow", "driving", "travel", "moving"],
                "negative": []
            },
            "CURRENCY": {
                "positive": ["costs", "price", "worth", "pay", "earn", "buy", "sell",
                             "salary", "fee", "charge", "spend", "budget", "total"],
                "negative": []
            },
            "ORDINAL": {
                "positive": ["came", "got", "rank", "position", "place", "finish",
                             "floor", "row", "seat"],
                "negative": []
            },
            "FRACTION": {
                "positive": ["half", "quarter", "third", "part", "fraction",
                             "ratio", "proportion"],
                "negative": []
            }
        }

        # Compiled patterns for fast matching
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> List[Dict]:
        """Compile all detection patterns with priorities."""
        return [
            # --- Highly specific patterns first ---
            {
                "category": "TIME",
                "subcategory": "usual_time",
                "pattern": re.compile(r'\b([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?\s*(AM|PM|am|pm)?\b'),
                "priority": 10,
                "rule_type": "time"
            },
            {
                "category": "TIME",
                "subcategory": "time_quantity",
                "pattern": re.compile(r"\b\d{1,2}'\d{1,2}\"\B"),
                "priority": 10,
                "rule_type": "time_quantity"
            },
            {
                "category": "DATE",
                "subcategory": "date",
                "pattern": re.compile(r'\b(0?[1-9]|[12][0-9]|3[01])[-/](0?[1-9]|1[0-2])[-/](19|20)?\d{2}\b'),
                "priority": 10,
                "rule_type": "date"
            },
            {
                "category": "DATE",
                "subcategory": "date_format",
                "pattern": re.compile(r'\b\d{1,2}(st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(\s+\d{4})?\b', re.IGNORECASE),
                "priority": 9,
                "rule_type": "date_format"
            },
            {
                "category": "FRACTION",
                "subcategory": "mixed_fraction",
                "pattern": re.compile(r'\b\d+\+\d+/\d+\b'),
                "priority": 9,
                "rule_type": "mixed_fraction"
            },
            {
                "category": "FRACTION",
                "subcategory": "normal_fraction",
                "pattern": re.compile(r'\b\d+/\d+\b'),
                "priority": 8,
                "rule_type": "fraction"
            },
            # --- Units (specific) ---
            {
                "category": "UNIT",
                "subcategory": "speed",
                "pattern": re.compile(r'\b\d+(\.\d+)?\s*(kmph|km/hr|km/h|mph|m/s|kph)\b', re.IGNORECASE),
                "priority": 9,
                "rule_type": "speed_unit"
            },
            {
                "category": "UNIT",
                "subcategory": "area",
                "pattern": re.compile(r'\b\d+(\.\d+)?\s*sq\.?\s*(ft|m|km|yd)\b', re.IGNORECASE),
                "priority": 9,
                "rule_type": "area_unit"
            },
            {
                "category": "UNIT",
                "subcategory": "volume",
                "pattern": re.compile(r'\b\d+(\.\d+)?\s*cu\.?\s*(ft|m|in|yd)\b', re.IGNORECASE),
                "priority": 9,
                "rule_type": "volume_unit"
            },
            {
                "category": "UNIT",
                "subcategory": "degree",
                "pattern": re.compile(r'\b\d+(\.\d+)?\s*°?\s*(C|F|Celsius|Fahrenheit)\b'),
                "priority": 9,
                "rule_type": "temperature"
            },
            {
                "category": "UNIT",
                "subcategory": "weight",
                "pattern": re.compile(r'\b\d+(\.\d+)?\s*(kg|gram|grams|g|ton|tons|mg|lb|lbs)\b', re.IGNORECASE),
                "priority": 8,
                "rule_type": "weight_unit"
            },
            {
                "category": "UNIT",
                "subcategory": "unit_of_length",
                "pattern": re.compile(r'\b\d+(\.\d+)?\s*(ft|feet|yd|yards|mi|miles|cm|centimeters?|m|meters?|km|kilometers?|in|inches?|inch)\b', re.IGNORECASE),
                "priority": 8,
                "rule_type": "length_unit"
            },
            {
                "category": "UNIT",
                "subcategory": "size",
                "pattern": re.compile(r'\b\d+(\.\d+)?\s*(MB|GB|KB|TB|byte|bytes)\b', re.IGNORECASE),
                "priority": 8,
                "rule_type": "unit_with_plural"
            },
            {
                "category": "UNIT",
                "subcategory": "time_unit",
                "pattern": re.compile(r'\b\d+(\.\d+)?\s*(sec|secs|min|mins|hr|hrs|hour|hours|ms|milliseconds?)\b', re.IGNORECASE),
                "priority": 8,
                "rule_type": "time_unit"
            },
            # --- Currency ---
            {
                "category": "UNIT",
                "subcategory": "currency",
                "pattern": re.compile(r'[\$€£₹]\s*\d+(\.\d{1,2})?|\b\d+(\.\d{1,2})?\s*(USD|EUR|GBP|INR|Rs\.?)\b'),
                "priority": 9,
                "rule_type": "currency"
            },
            # --- Character Reading ---
            {
                "category": "CHARACTER_READING",
                "subcategory": "samsung_nes",
                "pattern": re.compile(r'\bS\d{1,2}(Ultra|Plus|FE)?\b'),
                "priority": 9,
                "rule_type": "named_entity"
            },
            {
                "category": "CHARACTER_READING",
                "subcategory": "other_specific_nes",
                "pattern": re.compile(r'\b([A-Z][0-9]+|[0-9]+[A-Z])\b'),
                "priority": 7,
                "rule_type": "alphanumeric_entity"
            },
            {
                "category": "CHARACTER_READING",
                "subcategory": "initials_prefix",
                "pattern": re.compile(r'\b(Mr|Mrs|Ms|Dr|Prof|Shri|Sri|c/o|D/o|S/o)\.?\b'),
                "priority": 9,
                "rule_type": "prefix_expand"
            },
            {
                "category": "CHARACTER_READING",
                "subcategory": "acronym",
                "pattern": re.compile(r'\b[A-Z]{2,6}\b'),
                "priority": 5,
                "rule_type": "acronym"
            },
            # --- Number patterns ---
            {
                "category": "NUMBER",
                "subcategory": "comma_integer",
                "pattern": re.compile(r'\b\d{1,2}(,\d{2})*,\d{3}\b|\b\d+(,\d{3})+\b'),
                "priority": 8,
                "rule_type": "comma_separated"
            },
            {
                "category": "NUMBER",
                "subcategory": "roman_number",
                "pattern": re.compile(r'\b(M{0,4})(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\b'),
                "priority": 6,
                "rule_type": "roman_to_cardinal"
            },
            {
                "category": "NUMBER",
                "subcategory": "ordinal",
                "pattern": re.compile(r'\b\d+(st|nd|rd|th)\b'),
                "priority": 8,
                "rule_type": "ordinal"
            },
            {
                "category": "NUMBER",
                "subcategory": "special_code",
                "pattern": re.compile(r'\b[0-9.]+E[+\-][0-9]+\b|\b\+?[0-9]{1,3}[-\s]?[0-9]{5,15}\b'),
                "priority": 7,
                "rule_type": "digit_by_digit"
            },
            # --- Emoji ---
            {
                "category": "EMOJI",
                "subcategory": "facial_expression",
                "pattern": re.compile(r'[😊😢😂😍😡😮😴🙂😐😤]|[:;]-?[()DPp|]'),
                "priority": 9,
                "rule_type": "emoji_facial"
            },
            {
                "category": "EMOJI",
                "subcategory": "eatables",
                "pattern": re.compile(r'[☕🍵🍰🍕🍔🍎🍹🍷]'),
                "priority": 9,
                "rule_type": "emoji_food"
            },
            {
                "category": "EMOJI",
                "subcategory": "others",
                "pattern": re.compile(r'[❤️💙⭐👍👎🌟💯]'),
                "priority": 9,
                "rule_type": "emoji_other"
            },
            # --- Extra Requests ---
            {
                "category": "EXTRA_REQUESTS",
                "subcategory": "weekdays",
                "pattern": re.compile(r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b'),
                "priority": 8,
                "rule_type": "weekday"
            },
            {
                "category": "EXTRA_REQUESTS",
                "subcategory": "months",
                "pattern": re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|June|July|August|September|October|November|December)\b'),
                "priority": 7,
                "rule_type": "month"
            },
            {
                "category": "EXTRA_REQUESTS",
                "subcategory": "directions",
                "pattern": re.compile(r'\b(North|South|East|West|NE|NW|SE|SW)\b'),
                "priority": 6,
                "rule_type": "direction"
            },
            # --- Exception List ---
            {
                "category": "EXCEPTION_LIST",
                "subcategory": "word_reading",
                "pattern": re.compile(r'\b(live|read|lead|wind|tear|row|bow|close|wound)\b', re.IGNORECASE),
                "priority": 6,
                "rule_type": "homophone"
            },
            # --- Named Entity ---
            {
                "category": "NAMED_ENTITY",
                "subcategory": "local_named_entity",
                "pattern": re.compile(r'\b[A-Z][a-z]{2,}(\s[A-Z][a-z]{2,})+\b'),
                "priority": 4,
                "rule_type": "named_entity_local"
            },
            # --- Fallback number patterns ---
            {
                "category": "NUMBER",
                "subcategory": "cardinal",
                "pattern": re.compile(r'\b[0-9]{1,4}\b'),
                "priority": 3,
                "rule_type": "cardinal"
            },
            {
                "category": "NUMBER",
                "subcategory": "cardinal_digit",
                "pattern": re.compile(r'\b[0-9]{5,}\b'),
                "priority": 4,
                "rule_type": "digit_by_digit"
            },
        ]

    def classify(self, text: str, lang_data: dict = None) -> Dict:
        """
        Classify text and return detected category, subcategory, matched token,
        confidence score, and reasoning.
        If lang_data is provided, it uses the language's specific DFA patterns for matching.
        """
        matches = []

        # 1. First run the ML heuristics to gather contextual candidates
        for pattern_def in self.patterns:
            m = pattern_def["pattern"].search(text)
            if m:
                matched_token = m.group(0)
                base_score = pattern_def["priority"]
                context_boost = self._compute_context_boost(
                    text, m.start(), m.end(),
                    pattern_def["category"], pattern_def.get("subcategory", "")
                )
                final_score = base_score + context_boost

                matches.append({
                    "category": pattern_def["category"],
                    "subcategory": pattern_def["subcategory"],
                    "rule_type": pattern_def["rule_type"],
                    "matched_token": matched_token,
                    "score": final_score,
                    "context_boost": context_boost,
                    "span": (m.start(), m.end()),
                    "source": "ML"
                })

        # 2. Run DFA patterns if lang_data is provided
        if lang_data:
            categories = lang_data.get("categories", {})
            for cat_name, cat_data in categories.items():
                for subcat_name, subcat_data in cat_data.get("subcategories", {}).items():
                    dfa_pattern = subcat_data.get("dfa_pattern", "")
                    if dfa_pattern:
                        try:
                            # Use search instead of match for substring matching if pattern isn't anchored
                            m = re.search(dfa_pattern, text)
                            if m:
                                matched_token = m.group(0)
                                # DFA matches get a high base score
                                base_score = 11.0 
                                context_boost = self._compute_context_boost(
                                    text, m.start(), m.end(),
                                    cat_name, subcat_name
                                )
                                matches.append({
                                    "category": cat_name,
                                    "subcategory": subcat_name,
                                    "rule_type": subcat_data.get("rule_type", "generic"),
                                    "matched_token": matched_token,
                                    "score": base_score + context_boost,
                                    "context_boost": context_boost,
                                    "span": (m.start(), m.end()),
                                    "source": "DFA"
                                })
                        except re.error:
                            pass

        if not matches:
            return self._fallback_result(text)

        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        best = matches[0]

        # Resolve PINCODE vs CARDINAL for 6-digit numbers
        best = self._resolve_pincode_vs_cardinal(text, best, matches)

        return {
            "detected_category": best["category"],
            "detected_subcategory": best["subcategory"],
            "rule_type": best["rule_type"],
            "matched_token": best["matched_token"],
            "confidence": min(1.0, best["score"] / 12.0),
            "reasoning": self._build_reasoning(text, best, matches),
            "source": best.get("source", "ML"),
            "all_candidates": [
                {
                    "category": m["category"],
                    "subcategory": m["subcategory"],
                    "score": m["score"],
                    "token": m["matched_token"],
                    "source": m.get("source", "ML")
                }
                for m in matches[:5]
            ]
        }

    def _compute_context_boost(self, text: str, start: int, end: int,
                                category: str, subcategory: str) -> float:
        """Compute context-based score boost by analyzing surrounding words."""
        # Extract a window of words around the match
        window_start = max(0, start - 50)
        window_end = min(len(text), end + 50)
        context = text[window_start:window_end].lower()
        context_words = set(re.findall(r'\b\w+\b', context))

        boost = 0.0
        key = f"{category}_{subcategory}".lower()

        # Check against known context keyword sets
        for ctx_key, ctx_data in self.context_keywords.items():
            ctx_key_lower = ctx_key.lower()
            if ctx_key_lower in key or key.startswith(ctx_key_lower.split('_')[0].lower()):
                positives = set(ctx_data.get("positive", []))
                negatives = set(ctx_data.get("negative", []))
                pos_hits = len(context_words & positives)
                neg_hits = len(context_words & negatives)
                boost += pos_hits * 1.5 - neg_hits * 2.0

        return max(-3.0, min(3.0, boost))  # clamp to [-3, 3]

    def _resolve_pincode_vs_cardinal(self, text: str, best: Dict,
                                     all_matches: List[Dict]) -> Dict:
        """
        Special disambiguation for 6-digit numbers:
        CARDINAL if rank/score context, PINCODE otherwise.
        """
        token = best.get("matched_token", "")
        if re.match(r'^[1-9][0-9]{5}$', token):
            text_lower = text.lower()
            pincode_signals = ["pin", "pincode", "zip", "postal", "post code"]
            cardinal_signals = ["rank", "score", "roll", "id", "year"]

            is_pin = any(sig in text_lower for sig in pincode_signals)
            is_cardinal = any(sig in text_lower for sig in cardinal_signals)

            if is_cardinal:
                if best["category"] in ("NUMBER",) and best.get("rule_type") == "digit_by_digit":
                    return {**best, "category": "NUMBER", "subcategory": "cardinal_million_billion",
                            "rule_type": "cardinal"}
            else:
                return {
                    "category": "PINCODE",
                    "subcategory": "pincode",
                    "rule_type": "digit_by_digit",
                    "matched_token": token,
                    "score": 12.0,
                    "context_boost": 3.0 if is_pin else 0.0,
                    "span": best.get("span", (0, 0))
                }

        return best

    def _fallback_result(self, text: str) -> Dict:
        """Return a default result when no pattern matches."""
        # Check if pure text
        if re.match(r'^[A-Za-z\s]+$', text.strip()):
            return {
                "detected_category": "CHARACTER_READING",
                "detected_subcategory": "word_spell_out",
                "rule_type": "spell_out",
                "matched_token": text.strip(),
                "confidence": 0.3,
                "reasoning": "No specific pattern matched; treating as plain text",
                "all_candidates": []
            }
        return {
            "detected_category": "NUMBER",
            "detected_subcategory": "cardinal",
            "rule_type": "cardinal",
            "matched_token": text.strip(),
            "confidence": 0.2,
            "reasoning": "Fallback classification",
            "all_candidates": []
        }

    def _build_reasoning(self, text: str, best: Dict, all_matches: List[Dict]) -> str:
        """Build a human-readable reasoning string."""
        parts = [
            f"Matched token: '{best['matched_token']}'",
            f"Pattern priority: {best['score'] - best.get('context_boost', 0):.0f}",
            f"Context boost: {best.get('context_boost', 0):+.1f}",
            f"Final score: {best['score']:.1f}"
        ]
        if best.get('context_boost', 0) > 0:
            parts.append("Context keywords reinforced this category")
        elif best.get('context_boost', 0) < 0:
            parts.append("Context keywords reduced confidence in this category")
        if len(all_matches) > 1:
            runner = all_matches[1] if all_matches[0] == best else all_matches[0]
            parts.append(f"Runner-up: {runner['category']}/{runner['subcategory']} (score {runner['score']:.1f})")
        return "; ".join(parts)