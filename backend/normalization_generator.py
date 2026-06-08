"""
Normalization Rule Generator for TTS Text Normalization
Generates normalization rules from language resource JSON files.
"""

import json
import re
from typing import Dict, List, Any, Optional


class NormalizationRuleGenerator:
    """Generates text normalization rules for TTS systems."""

    def generate_rules_for_category(self, language_data: Dict, category: str,
                                    subcategory: str, subcat_data: Dict) -> Dict:
        """Generate normalization rules for a specific subcategory."""
        rule_type = subcat_data.get("rule_type", "generic")
        lang = language_data["language"]

        rule = {
            "id": f"{lang}_{category}_{subcategory}",
            "language": lang,
            "category": category,
            "subcategory": subcategory,
            "rule_type": rule_type,
            "description": subcat_data.get("description", ""),
            "examples": subcat_data.get("examples", []),
            "dfa_pattern": subcat_data.get("dfa_pattern", ""),
            "remarks": subcat_data.get("remarks", ""),
            "normalization_steps": [],
            "output_format": "",
            "ssml_template": ""
        }

        # Build normalization steps based on rule type
        steps, output_format, ssml_key = self._build_steps(rule_type, subcat_data, language_data)
        rule["normalization_steps"] = steps
        rule["output_format"] = output_format
        rule["ssml_key"] = ssml_key
        rule["ssml_template"] = language_data.get("ssml_templates", {}).get(ssml_key, "")

        return rule

    def _build_steps(self, rule_type: str, subcat_data: Dict, language_data: Dict):
        """Build normalization steps for a given rule type."""
        mappings = language_data.get("mappings", {})

        if rule_type == "digit_by_digit":
            pron_map = mappings.get("digits", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "SPLIT_DIGITS", "description": "Split input into individual digits"},
                {"step": 3, "action": "MAP_DIGITS",
                 "description": "Map each digit to spoken word",
                 "mapping": pron_map if pron_map else "use_language_digit_map"},
                {"step": 4, "action": "JOIN_WITH_PAUSE",
                 "description": "Join digit words with short pause",
                 "separator": " "},
                {"step": 5, "action": "WRAP_SSML",
                 "template": "<say-as interpret-as='characters'>{input}</say-as>"}
            ]
            return steps, "{digit1} {digit2} ... {digitN}", "digit_by_digit"

        elif rule_type == "cardinal":
            scale_words = mappings.get("cardinal", {}).get("scale_words", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "PARSE_NUMBER", "description": "Parse integer value"},
                {"step": 3, "action": "APPLY_SCALE",
                 "description": "Apply Indian/local number scale (lakh, crore etc.)",
                 "scale_map": scale_words},
                {"step": 4, "action": "COMPOSE_SPOKEN_FORM",
                 "description": "Compose full spoken form using scale words"},
                {"step": 5, "action": "WRAP_SSML",
                 "template": "<say-as interpret-as='cardinal'>{input}</say-as>"}
            ]
            return steps, "spoken cardinal number", "cardinal"

        elif rule_type == "ordinal":
            suffix_map = mappings.get("ordinal", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "EXTRACT_BASE_NUMBER",
                 "description": "Extract numeric part (strip st/nd/rd/th)"},
                {"step": 3, "action": "LOOKUP_ORDINAL",
                 "description": "Look up ordinal word for number",
                 "lookup_table": suffix_map if suffix_map else "compute_ordinal"},
                {"step": 4, "action": "WRAP_SSML",
                 "template": "<say-as interpret-as='ordinal'>{input}</say-as>"}
            ]
            return steps, "ordinal spoken word (first, second...)", "ordinal"

        elif rule_type == "fraction":
            frac_words = mappings.get("fraction", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "SPLIT_ON_SLASH",
                 "description": "Split into numerator and denominator"},
                {"step": 3, "action": "LOOKUP_COMMON_FRACTIONS",
                 "description": "Use common fraction words if available",
                 "lookup": frac_words if frac_words else {}},
                {"step": 4, "action": "FALLBACK_COMPOSE",
                 "description": "If not in lookup, compose as 'N over D'"},
                {"step": 5, "action": "WRAP_SSML",
                 "template": "<say-as interpret-as='fraction'>{input}</say-as>"}
            ]
            return steps, "fraction spoken form (e.g., 'one half')", "fraction"

        elif rule_type == "mixed_fraction":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "SPLIT_ON_PLUS",
                 "description": "Split into whole number and fraction parts"},
                {"step": 3, "action": "PROCESS_WHOLE", "description": "Convert whole number to cardinal"},
                {"step": 4, "action": "PROCESS_FRACTION", "description": "Convert fraction part"},
                {"step": 5, "action": "JOIN", "description": "Join: 'N and F'"}
            ]
            return steps, "N and F (e.g., five and nine halves)", "fraction"

        elif rule_type == "date":
            month_map = mappings.get("month", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "DETECT_FORMAT",
                 "description": "Detect date format (dmy/mdy/ymd)"},
                {"step": 3, "action": "EXTRACT_COMPONENTS",
                 "description": "Extract day, month, year"},
                {"step": 4, "action": "MAP_MONTH",
                 "description": "Convert month number to name",
                 "month_map": month_map if month_map else "use_language_month_map"},
                {"step": 5, "action": "APPLY_ORDINAL_TO_DAY",
                 "description": "Convert day to ordinal (e.g., 1 -> first)"},
                {"step": 6, "action": "COMPOSE_DATE",
                 "description": "Compose: 'Nth MonthName Year'"},
                {"step": 7, "action": "WRAP_SSML",
                 "template": "<say-as interpret-as='date' format='dmy'>{input}</say-as>"}
            ]
            return steps, "Nth MonthName Year (e.g., eleventh July 2025)", "date"

        elif rule_type == "date_format":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "DETECT_FORMAT", "supported_formats": subcat_data.get("formats", [])},
                {"step": 3, "action": "PARSE_COMPONENTS", "description": "Parse date components"},
                {"step": 4, "action": "NORMALIZE_TO_SPOKEN", "description": "Convert to natural language date"}
            ]
            return steps, "natural language date", "date"

        elif rule_type == "time":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "EXTRACT_COMPONENTS",
                 "description": "Extract hours, minutes, seconds, AM/PM"},
                {"step": 3, "action": "DETECT_FORMAT",
                 "description": "12hr vs 24hr format"},
                {"step": 4, "action": "CONVERT_24_TO_12",
                 "description": "If 24hr, convert to 12hr + AM/PM"},
                {"step": 5, "action": "COMPOSE_TIME",
                 "description": "Compose: 'H hours M minutes'"},
                {"step": 6, "action": "WRAP_SSML",
                 "template": "<say-as interpret-as='time' format='hms12'>{input}</say-as>"}
            ]
            return steps, "spoken time (e.g., 'twelve thirty PM')", "time"

        elif rule_type in ("spell_out", "acronym"):
            alpha_map = mappings.get("alphabet", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "SPLIT_INTO_LETTERS",
                 "description": "Split string into individual letters"},
                {"step": 3, "action": "MAP_LETTERS",
                 "description": "Map each letter to spoken name",
                 "alphabet_map": alpha_map if alpha_map else "use_language_alphabet"},
                {"step": 4, "action": "JOIN_WITH_PAUSE",
                 "separator": " "},
                {"step": 5, "action": "WRAP_SSML",
                 "template": "<say-as interpret-as='spell-out'>{input}</say-as>"}
            ]
            return steps, "spelled out letters (e.g., 'ay bee see')", "spell_out"

        elif rule_type == "prefix_expand":
            prefix_map = mappings.get("prefix", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "STRIP_DOT", "description": "Remove trailing dot if present"},
                {"step": 3, "action": "LOOKUP_PREFIX",
                 "description": "Look up full form from prefix map",
                 "prefix_map": prefix_map},
                {"step": 4, "action": "FALLBACK_SPELL_OUT",
                 "description": "If not found in map, spell out letters"}
            ]
            return steps, "expanded prefix (e.g., Mr -> Mister)", "default"

        elif rule_type in ("unit_with_plural", "length_unit", "weight_unit", "time_unit"):
            unit_map = mappings.get("unit", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "EXTRACT_NUMBER_AND_UNIT",
                 "description": "Split into numeric value and unit abbreviation"},
                {"step": 3, "action": "CONVERT_NUMBER_TO_CARDINAL",
                 "description": "Convert number to spoken cardinal form"},
                {"step": 4, "action": "LOOKUP_UNIT",
                 "description": "Look up unit full form from unit map",
                 "unit_map": unit_map},
                {"step": 5, "action": "APPLY_PLURAL_RULE",
                 "description": "Use singular if value==1, plural otherwise"},
                {"step": 6, "action": "COMPOSE",
                 "description": "Compose: '<number> <unit>'"}
            ]
            return steps, "number with unit (e.g., 'ten feet', '5 kilograms')", "unit"

        elif rule_type == "currency":
            currency_map = mappings.get("currency", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "EXTRACT_SYMBOL_AND_AMOUNT",
                 "description": "Identify currency symbol/code and numeric value"},
                {"step": 3, "action": "LOOKUP_CURRENCY_WORD",
                 "description": "Convert symbol to currency name",
                 "currency_map": currency_map},
                {"step": 4, "action": "HANDLE_DECIMAL",
                 "description": "Handle cents/paise as separate spoken unit"},
                {"step": 5, "action": "COMPOSE",
                 "description": "Compose: '<amount> <currency> and <cents> <subunit>'"}
            ]
            return steps, "spoken currency (e.g., 'ten dollars and fifty cents')", "default"

        elif rule_type == "roman_to_cardinal":
            roman_map = mappings.get("roman", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "VALIDATE_ROMAN",
                 "description": "Validate roman numeral string"},
                {"step": 3, "action": "CONVERT_ROMAN_TO_INTEGER",
                 "description": "Convert roman numeral to integer value",
                 "roman_values": roman_map if roman_map else {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}},
                {"step": 4, "action": "CONVERT_INTEGER_TO_CARDINAL",
                 "description": "Convert integer to spoken cardinal form"}
            ]
            return steps, "spoken cardinal for roman numeral (e.g., XIV -> fourteen)", "cardinal"

        elif rule_type == "homophone":
            homophones = subcat_data.get("homophones", {})
            steps = [
                {"step": 1, "action": "MATCH_WORD",
                 "description": "Match homophone word",
                 "word_list": list(homophones.keys())},
                {"step": 2, "action": "ANALYZE_CONTEXT",
                 "description": "Analyze surrounding words for POS context"},
                {"step": 3, "action": "SELECT_PRONUNCIATION",
                 "description": "Select correct pronunciation based on context",
                 "options": homophones},
                {"step": 4, "action": "APPLY_PHONEME",
                 "description": "Apply selected phoneme/pronunciation"}
            ]
            return steps, "context-dependent pronunciation", "default"

        elif rule_type == "temperature":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "EXTRACT_VALUE_AND_SCALE",
                 "description": "Extract numeric value and C/F scale"},
                {"step": 3, "action": "CONVERT_NUMBER_TO_CARDINAL"},
                {"step": 4, "action": "MAP_SCALE",
                 "description": "C -> Celsius, F -> Fahrenheit"},
                {"step": 5, "action": "COMPOSE",
                 "description": "Compose: '<value> degrees <scale>'"}
            ]
            return steps, "spoken temperature (e.g., '37 degrees Celsius')", "default"

        elif rule_type == "comma_separated":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "REMOVE_COMMAS",
                 "description": "Strip commas to get integer value"},
                {"step": 3, "action": "PARSE_INTEGER_VALUE"},
                {"step": 4, "action": "APPLY_LAKH_CRORE_SCALE",
                 "description": "Use lakh/crore scale for Indian locale"},
                {"step": 5, "action": "COMPOSE_SPOKEN_FORM"}
            ]
            return steps, "spoken number with lakh/crore (e.g., 10,100 -> ten thousand one hundred)", "cardinal"

        elif rule_type == "area_unit":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "EXTRACT_PARTS", "description": "Extract number and unit"},
                {"step": 3, "action": "EXPAND_SQ", "description": "sq -> square"},
                {"step": 4, "action": "EXPAND_UNIT", "description": "ft -> feet, m -> meters"},
                {"step": 5, "action": "COMPOSE", "description": "Compose: '<N> square <unit>'"}
            ]
            return steps, "spoken area (e.g., 'ten square feet')", "unit"

        elif rule_type == "volume_unit":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "EXTRACT_PARTS"},
                {"step": 3, "action": "EXPAND_CU", "description": "cu -> cubic"},
                {"step": 4, "action": "EXPAND_UNIT"},
                {"step": 5, "action": "COMPOSE", "description": "Compose: '<N> cubic <unit>'"}
            ]
            return steps, "spoken volume (e.g., 'five cubic feet')", "unit"

        elif rule_type == "speed_unit":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "EXTRACT_NUMBER"},
                {"step": 3, "action": "NORMALIZE_UNIT",
                 "description": "kmph / km/hr -> kilometers per hour"},
                {"step": 4, "action": "COMPOSE"}
            ]
            return steps, "spoken speed (e.g., 'sixty kilometers per hour')", "unit"

        elif rule_type == "weekday":
            day_map = subcat_data.get("day_map", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "LOOKUP_FULL_DAY_NAME",
                 "description": "Expand abbreviation to full day name",
                 "day_map": day_map}
            ]
            return steps, "full day name (e.g., Mon -> Monday)", "default"

        elif rule_type == "month":
            month_map = subcat_data.get("month_map", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "LOOKUP_FULL_MONTH_NAME",
                 "description": "Expand abbreviation to full month name",
                 "month_map": month_map}
            ]
            return steps, "full month name (e.g., Jan -> January)", "default"

        elif rule_type == "direction":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "LOOKUP_DIRECTION",
                 "description": "Expand direction abbreviation",
                 "direction_map": subcat_data.get("direction_map", {})}
            ]
            return steps, "full direction name (e.g., NE -> North East)", "default"

        elif rule_type == "emoji_facial":
            steps = [
                {"step": 1, "action": "MATCH_EMOJI", "description": "Match emoji character or text emoticon"},
                {"step": 2, "action": "LOOKUP_EMOJI_DESCRIPTION",
                 "emoji_map": subcat_data.get("emoji_map", {})},
                {"step": 3, "action": "WRAP_IN_SPOKEN_CONTEXT",
                 "description": "e.g., 'smiley face emoji'"}
            ]
            return steps, "spoken emoji description (e.g., smile)", "default"

        elif rule_type in ("emoji_food", "emoji_other"):
            steps = [
                {"step": 1, "action": "MATCH_EMOJI"},
                {"step": 2, "action": "LOOKUP_DESCRIPTION",
                 "emoji_map": subcat_data.get("emoji_map", {})},
                {"step": 3, "action": "COMPOSE_SPOKEN"}
            ]
            return steps, "spoken emoji label", "default"

        elif rule_type == "named_entity_local":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "LOOKUP_IN_NE_DICTIONARY",
                 "description": "Check local named entity dictionary"},
                {"step": 3, "action": "APPLY_LOCAL_PHONEME_RULES",
                 "description": "Apply language-specific pronunciation"},
                {"step": 4, "action": "FALLBACK_READ_AS_IS",
                 "description": "If not in dictionary, read letters as-is"}
            ]
            return steps, "spoken local name with correct phonemes", "default"

        elif rule_type == "named_entity_foreign":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "LOOKUP_IN_FOREIGN_NE_DICTIONARY"},
                {"step": 3, "action": "APPLY_TRANSLITERATION_RULES",
                 "description": "Transliterate to local phonemes if needed"},
                {"step": 4, "action": "FALLBACK_READ_AS_IS"}
            ]
            return steps, "spoken foreign name with transliterated phonemes", "default"

        elif rule_type == "alphanumeric_entity":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "SPLIT_ALPHA_NUMERIC",
                 "description": "Separate alphabetic and numeric parts"},
                {"step": 3, "action": "SPELL_ALPHA_PART"},
                {"step": 4, "action": "CARDINAL_NUMERIC_PART"},
                {"step": 5, "action": "COMPOSE"}
            ]
            return steps, "spoken alphanumeric (e.g., G20 -> Gee Twenty, 5G -> Five Gee)", "default"

        elif rule_type == "gujarati_numeral":
            numeral_map = subcat_data.get("numeral_map", {})
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "CONVERT_GUJARATI_TO_ARABIC",
                 "description": "Map each Gujarati numeral to Arabic digit",
                 "numeral_map": numeral_map},
                {"step": 3, "action": "APPLY_CARDINAL_RULE",
                 "description": "Process resulting Arabic digits as cardinal"}
            ]
            return steps, "spoken Gujarati number", "cardinal"

        elif rule_type == "time_quantity":
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "EXTRACT_MINUTES_SECONDS",
                 "description": "Extract M'SS\" pattern"},
                {"step": 3, "action": "COMPOSE",
                 "description": "Compose: 'M minutes SS seconds'"}
            ]
            return steps, "spoken time quantity (e.g., 5 minutes 15 seconds)", "time"

        else:
            steps = [
                {"step": 1, "action": "MATCH_PATTERN", "pattern": subcat_data.get("dfa_pattern", "")},
                {"step": 2, "action": "APPLY_GENERIC_NORMALIZATION"}
            ]
            return steps, "normalized text", "default"

    def generate_all_rules(self, language_data: Dict,
                           selected_categories: Optional[List[str]] = None) -> Dict:
        """Generate normalization rules for all or selected categories."""
        result = {
            "language": language_data["language"],
            "language_name": language_data["language_name"],
            "generated_at": __import__('datetime').datetime.now().isoformat(),
            "normalization_rules": []
        }

        categories = language_data.get("categories", {})
        if selected_categories:
            categories = {k: v for k, v in categories.items() if k in selected_categories}

        for cat_name, cat_data in categories.items():
            for subcat_name, subcat_data in cat_data.get("subcategories", {}).items():
                rule = self.generate_rules_for_category(
                    language_data, cat_name, subcat_name, subcat_data
                )
                result["normalization_rules"].append(rule)

        return result