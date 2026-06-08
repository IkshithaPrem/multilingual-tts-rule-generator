"""
SSML Generator for TTS Text Normalization Framework
Generates Speech Synthesis Markup Language templates and instances.
"""

import re
from typing import Dict, List, Any, Optional


class SSMLGenerator:
    """Generates SSML markup for TTS systems."""

    # SSML interpret-as mappings per rule type
    RULE_TYPE_SSML_MAP = {
        "digit_by_digit":   "characters",
        "cardinal":          "cardinal",
        "ordinal":           "ordinal",
        "fraction":          "fraction",
        "mixed_fraction":    "fraction",
        "date":              "date",
        "date_format":       "date",
        "time":              "time",
        "time_quantity":     "time",
        "spell_out":         "spell-out",
        "acronym":           "spell-out",
        "roman_to_cardinal": "cardinal",
        "comma_separated":   "cardinal",
        "gujarati_numeral":  "cardinal",
        "named_entity_local": None,
        "named_entity_foreign": None,
        "prefix_expand":     None,
        "alphanumeric_entity": None,
        "unit_with_plural":  None,
        "length_unit":       None,
        "weight_unit":       None,
        "area_unit":         None,
        "volume_unit":       None,
        "speed_unit":        None,
        "time_unit":         None,
        "currency":          None,
        "temperature":       None,
        "weekday":           None,
        "month":             None,
        "direction":         None,
        "homophone":         None,
        "emoji_facial":      None,
        "emoji_food":        None,
        "emoji_other":       None,
    }

    def generate_ssml_rules(self, language_data: Dict,
                            selected_categories: Optional[List[str]] = None) -> Dict:
        """Generate SSML rules for all categories."""
        result = {
            "language": language_data["language"],
            "language_name": language_data["language_name"],
            "generated_at": __import__('datetime').datetime.now().isoformat(),
            "ssml_rules": [],
            "ssml_templates": language_data.get("ssml_templates", {}),
            "ssml_examples": []
        }

        categories = language_data.get("categories", {})
        if selected_categories:
            categories = {k: v for k, v in categories.items() if k in selected_categories}

        for cat_name, cat_data in categories.items():
            for subcat_name, subcat_data in cat_data.get("subcategories", {}).items():
                rule_type = subcat_data.get("rule_type", "generic")
                examples = subcat_data.get("examples", [])

                ssml_rule = self._build_ssml_rule(
                    language_data, cat_name, subcat_name, subcat_data, rule_type, examples
                )
                result["ssml_rules"].append(ssml_rule)

                # Generate example SSML for each example
                for ex in examples[:2]:  # max 2 examples per rule
                    ssml_ex = self._generate_example_ssml(ex, rule_type, subcat_data)
                    if ssml_ex:
                        result["ssml_examples"].append({
                            "category": cat_name,
                            "subcategory": subcat_name,
                            "input": ex,
                            "ssml_output": ssml_ex
                        })

        return result

    def _build_ssml_rule(self, language_data: Dict, category: str, subcategory: str,
                         subcat_data: Dict, rule_type: str, examples: List) -> Dict:
        """Build an SSML rule definition."""
        interpret_as = self.RULE_TYPE_SSML_MAP.get(rule_type)
        templates = language_data.get("ssml_templates", {})

        rule = {
            "id": f"{language_data['language']}_{category}_{subcategory}",
            "category": category,
            "subcategory": subcategory,
            "rule_type": rule_type,
            "pattern": subcat_data.get("dfa_pattern", ""),
            "ssml_interpret_as": interpret_as,
            "prosody_rate": self._get_prosody_rate(rule_type),
            "prosody_pitch": self._get_prosody_pitch(rule_type),
            "templates": {}
        }

        # Add relevant templates
        if interpret_as:
            rule["templates"]["primary"] = f"<say-as interpret-as='{interpret_as}'>" + "{INPUT}" + "</say-as>"
        else:
            rule["templates"]["primary"] = self._build_custom_ssml(rule_type, subcat_data)

        # Wrapped in speak tag
        rule["templates"]["full"] = f"<speak>{rule['templates']['primary']}</speak>"

        # With prosody
        rate = rule["prosody_rate"]
        if rate:
            rule["templates"]["with_prosody"] = (
                f"<speak><prosody rate='{rate}'>{rule['templates']['primary']}</prosody></speak>"
            )

        # Date/time need format attribute
        if rule_type in ("date", "date_format"):
            formats = subcat_data.get("formats", ["dmy"])
            rule["templates"]["date_formats"] = {
                fmt: f"<say-as interpret-as='date' format='{fmt}'>" + "{INPUT}" + "</say-as>"
                for fmt in (formats if formats else ["dmy", "mdy", "ymd"])
            }

        if rule_type in ("time", "time_quantity"):
            rule["templates"]["time_formats"] = {
                "hms12": "<say-as interpret-as='time' format='hms12'>" + "{INPUT}" + "</say-as>",
                "hms24": "<say-as interpret-as='time' format='hms24'>" + "{INPUT}" + "</say-as>",
                "hm":    "<say-as interpret-as='time' format='hm'>" + "{INPUT}" + "</say-as>"
            }

        return rule

    def _build_custom_ssml(self, rule_type: str, subcat_data: Dict) -> str:
        """Build custom SSML for rules that don't have a direct interpret-as."""
        if rule_type == "prefix_expand":
            return "<sub alias='{EXPANDED}'>{INPUT}</sub>"

        elif rule_type in ("unit_with_plural", "length_unit", "weight_unit",
                           "volume_unit", "area_unit", "speed_unit", "time_unit"):
            return (
                "<say-as interpret-as='cardinal'>{NUMBER}</say-as> "
                "<w role='amazon:VBD'>{UNIT}</w>"
            )

        elif rule_type == "currency":
            return (
                "<say-as interpret-as='cardinal'>{AMOUNT}</say-as> {CURRENCY_WORD} "
                "<break time='50ms'/>"
                "<say-as interpret-as='cardinal'>{CENTS}</say-as> {SUBUNIT}"
            )

        elif rule_type == "temperature":
            return (
                "<say-as interpret-as='cardinal'>{VALUE}</say-as> degrees "
                "<sub alias='{SCALE_FULL}'>{SCALE}</sub>"
            )

        elif rule_type in ("named_entity_local", "named_entity_foreign"):
            return "<phoneme alphabet='ipa' ph='{PHONEME}'>{INPUT}</phoneme>"

        elif rule_type == "alphanumeric_entity":
            return (
                "<say-as interpret-as='spell-out'>{ALPHA_PART}</say-as>"
                "<say-as interpret-as='cardinal'>{NUMERIC_PART}</say-as>"
            )

        elif rule_type == "homophone":
            return "<phoneme alphabet='ipa' ph='{CONTEXT_PHONEME}'>{INPUT}</phoneme>"

        elif rule_type in ("emoji_facial", "emoji_food", "emoji_other"):
            return "<sub alias='{EMOJI_DESCRIPTION}'>{INPUT}</sub>"

        elif rule_type in ("weekday", "month", "direction"):
            return "<sub alias='{EXPANDED}'>{INPUT}</sub>"

        elif rule_type == "comma_separated":
            return "<say-as interpret-as='cardinal'>{STRIPPED_NUMBER}</say-as>"

        elif rule_type == "gujarati_numeral":
            return "<say-as interpret-as='cardinal'>{ARABIC_EQUIVALENT}</say-as>"

        elif rule_type == "time_quantity":
            return (
                "<say-as interpret-as='cardinal'>{MINUTES}</say-as> minutes "
                "<say-as interpret-as='cardinal'>{SECONDS}</say-as> seconds"
            )

        else:
            return "{INPUT}"

    def _get_prosody_rate(self, rule_type: str) -> Optional[str]:
        """Determine appropriate prosody rate for rule type."""
        slow_rules = {"digit_by_digit", "spell_out", "acronym"}
        medium_rules = {"date", "time"}
        if rule_type in slow_rules:
            return "slow"
        if rule_type in medium_rules:
            return "medium"
        return None

    def _get_prosody_pitch(self, rule_type: str) -> Optional[str]:
        """Determine appropriate prosody pitch for rule type."""
        return None  # Default pitch for most rules

    def _generate_example_ssml(self, example: str, rule_type: str,
                                subcat_data: Dict) -> Optional[str]:
        """Generate example SSML output for an input string."""
        try:
            interpret_as = self.RULE_TYPE_SSML_MAP.get(rule_type)

            if rule_type == "digit_by_digit":
                return f"<speak><say-as interpret-as='characters'>{example}</say-as></speak>"

            elif rule_type == "cardinal":
                return f"<speak><say-as interpret-as='cardinal'>{example}</say-as></speak>"

            elif rule_type == "ordinal":
                num = re.sub(r'(st|nd|rd|th)$', '', example)
                return f"<speak><say-as interpret-as='ordinal'>{num}</say-as></speak>"

            elif rule_type == "fraction":
                return f"<speak><say-as interpret-as='fraction'>{example}</say-as></speak>"

            elif rule_type == "date":
                return f"<speak><say-as interpret-as='date' format='dmy'>{example}</say-as></speak>"

            elif rule_type == "time":
                return f"<speak><say-as interpret-as='time' format='hms12'>{example}</say-as></speak>"

            elif rule_type in ("spell_out", "acronym"):
                return f"<speak><say-as interpret-as='spell-out'>{example}</say-as></speak>"

            elif rule_type == "prefix_expand":
                prefix_map = subcat_data.get("prefix_map", {})
                expanded = prefix_map.get(example, example)
                return f"<speak><sub alias='{expanded}'>{example}</sub></speak>"

            elif rule_type in ("unit_with_plural", "length_unit", "weight_unit"):
                m = re.match(r'^([0-9.]+)\s*([A-Za-z]+)$', example)
                if m:
                    num, unit = m.group(1), m.group(2)
                    unit_map = subcat_data.get("unit_map", {})
                    unit_entry = unit_map.get(unit, {})
                    if isinstance(unit_entry, dict):
                        full_unit = unit_entry.get("plural" if float(num) != 1 else "singular", unit)
                    else:
                        full_unit = unit_entry or unit
                    return (f"<speak><say-as interpret-as='cardinal'>{num}</say-as> "
                            f"<w>{full_unit}</w></speak>")

            elif rule_type == "weekday":
                day_map = subcat_data.get("day_map", {})
                full = day_map.get(example, example)
                return f"<speak><sub alias='{full}'>{example}</sub></speak>"

            elif rule_type == "month":
                month_map = subcat_data.get("month_map", {})
                full = month_map.get(example, example)
                return f"<speak><sub alias='{full}'>{example}</sub></speak>"

            elif interpret_as:
                return f"<speak><say-as interpret-as='{interpret_as}'>{example}</say-as></speak>"

            return f"<speak>{example}</speak>"

        except Exception:
            return f"<speak>{example}</speak>"