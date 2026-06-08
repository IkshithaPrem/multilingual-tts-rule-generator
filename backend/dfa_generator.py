"""
DFA Rule Generator for TTS Text Normalization
Generates Deterministic Finite Automaton rules from language resource JSON files.
"""

import json
import re
from typing import Dict, List, Any, Optional


class DFAState:
    def __init__(self, state_id: str, is_accepting: bool = False, label: str = ""):
        self.state_id = state_id
        self.is_accepting = is_accepting
        self.label = label
        self.transitions: Dict[str, str] = {}

    def to_dict(self):
        return {
            "id": self.state_id,
            "label": self.label,
            "is_accepting": self.is_accepting,
            "transitions": self.transitions
        }


class DFAGenerator:
    """Generates DFA rules for text normalization categories."""

    def __init__(self):
        self.state_counter = 0

    def _new_state_id(self, prefix: str = "q") -> str:
        self.state_counter += 1
        return f"{prefix}_{self.state_counter}"

    def generate_dfa_for_pattern(self, pattern: str, category: str, subcategory: str, rule_type: str) -> Dict:
        """Generate DFA states and transitions for a regex pattern."""
        self.state_counter = 0

        dfa = {
            "category": category,
            "subcategory": subcategory,
            "rule_type": rule_type,
            "pattern": pattern,
            "states": [],
            "transitions": [],
            "initial_state": "q_0",
            "accepting_states": []
        }

        # Generate DFA based on rule type
        if rule_type == "digit_by_digit":
            dfa.update(self._generate_digit_dfa(category, subcategory))
        elif rule_type == "cardinal":
            dfa.update(self._generate_cardinal_dfa(category, subcategory))
        elif rule_type == "ordinal":
            dfa.update(self._generate_ordinal_dfa())
        elif rule_type == "fraction":
            dfa.update(self._generate_fraction_dfa())
        elif rule_type == "mixed_fraction":
            dfa.update(self._generate_mixed_fraction_dfa())
        elif rule_type == "date":
            dfa.update(self._generate_date_dfa())
        elif rule_type == "time":
            dfa.update(self._generate_time_dfa())
        elif rule_type in ("spell_out", "acronym"):
            dfa.update(self._generate_spell_out_dfa())
        elif rule_type == "prefix_expand":
            dfa.update(self._generate_prefix_dfa())
        elif rule_type in ("unit_with_plural", "length_unit", "weight_unit",
                           "area_unit", "volume_unit", "speed_unit", "time_unit"):
            dfa.update(self._generate_unit_dfa(rule_type))
        elif rule_type == "currency":
            dfa.update(self._generate_currency_dfa())
        elif rule_type == "roman_to_cardinal":
            dfa.update(self._generate_roman_dfa())
        elif rule_type == "homophone":
            dfa.update(self._generate_homophone_dfa())
        elif rule_type == "temperature":
            dfa.update(self._generate_temperature_dfa())
        elif rule_type == "comma_separated":
            dfa.update(self._generate_comma_dfa())
        elif rule_type == "weekday":
            dfa.update(self._generate_weekday_dfa())
        elif rule_type == "month":
            dfa.update(self._generate_month_dfa())
        elif rule_type == "date_format":
            dfa.update(self._generate_date_format_dfa())
        else:
            dfa.update(self._generate_generic_dfa(pattern))

        return dfa

    def _generate_digit_dfa(self, category: str, subcategory: str) -> Dict:
        """DFA for digit-by-digit reading (PIN codes, phone numbers)."""
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "FIRST_DIGIT", "is_accepting": False},
            {"id": "q2", "label": "MORE_DIGITS", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[0-9]", "to": "q1", "action": "read_digit"},
            {"from": "q1", "input": "[0-9]", "to": "q2", "action": "read_digit"},
            {"from": "q2", "input": "[0-9]", "to": "q2", "action": "read_digit"},
            {"from": "q0", "input": "[^0-9]", "to": "q_err", "action": "error"},
            {"from": "q1", "input": "[^0-9]", "to": "q_err", "action": "error"},
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q2"],
            "output_action": "pronounce_each_digit_separately"
        }

    def _generate_cardinal_dfa(self, category: str, subcategory: str) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "DIGIT", "is_accepting": True},
            {"id": "q2", "label": "MULTI_DIGIT", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[1-9]", "to": "q1", "action": "start_number"},
            {"from": "q0", "input": "0", "to": "q1", "action": "start_zero"},
            {"from": "q1", "input": "[0-9]", "to": "q2", "action": "append_digit"},
            {"from": "q2", "input": "[0-9]", "to": "q2", "action": "append_digit"},
            {"from": "q0", "input": "[^0-9]", "to": "q_err", "action": "error"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q1", "q2"],
            "output_action": "pronounce_full_number_value"
        }

    def _generate_ordinal_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "DIGITS", "is_accepting": False},
            {"id": "q2", "label": "SUFFIX_1", "is_accepting": False},
            {"id": "q3", "label": "SUFFIX_2_ACCEPT", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[0-9]", "to": "q1", "action": "read_digit"},
            {"from": "q1", "input": "[0-9]", "to": "q1", "action": "read_digit"},
            {"from": "q1", "input": "s|n|r|t", "to": "q2", "action": "start_suffix"},
            {"from": "q2", "input": "t|d|h", "to": "q3", "action": "complete_suffix"},
            {"from": "q3", "input": "\\b", "to": "q3", "action": "accept"},
            {"from": "q0", "input": "[^0-9]", "to": "q_err", "action": "error"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q3"],
            "output_action": "lookup_ordinal_word"
        }

    def _generate_fraction_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "NUMERATOR", "is_accepting": False},
            {"id": "q2", "label": "SLASH", "is_accepting": False},
            {"id": "q3", "label": "DENOMINATOR", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[0-9]", "to": "q1", "action": "read_numerator"},
            {"from": "q1", "input": "[0-9]", "to": "q1", "action": "read_numerator"},
            {"from": "q1", "input": "/", "to": "q2", "action": "read_slash"},
            {"from": "q2", "input": "[0-9]", "to": "q3", "action": "read_denominator"},
            {"from": "q3", "input": "[0-9]", "to": "q3", "action": "read_denominator"},
            {"from": "q0", "input": "[^0-9]", "to": "q_err", "action": "error"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q3"],
            "output_action": "pronounce_fraction"
        }

    def _generate_mixed_fraction_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "WHOLE_NUMBER", "is_accepting": False},
            {"id": "q2", "label": "PLUS_SIGN", "is_accepting": False},
            {"id": "q3", "label": "FRACTION_NUMERATOR", "is_accepting": False},
            {"id": "q4", "label": "FRACTION_SLASH", "is_accepting": False},
            {"id": "q5", "label": "FRACTION_DENOMINATOR", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[0-9]", "to": "q1", "action": "read_whole"},
            {"from": "q1", "input": "[0-9]", "to": "q1", "action": "read_whole"},
            {"from": "q1", "input": "+", "to": "q2", "action": "read_plus"},
            {"from": "q2", "input": "[0-9]", "to": "q3", "action": "read_numerator"},
            {"from": "q3", "input": "[0-9]", "to": "q3", "action": "read_numerator"},
            {"from": "q3", "input": "/", "to": "q4", "action": "read_slash"},
            {"from": "q4", "input": "[0-9]", "to": "q5", "action": "read_denominator"},
            {"from": "q5", "input": "[0-9]", "to": "q5", "action": "read_denominator"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q5"],
            "output_action": "pronounce_mixed_fraction"
        }

    def _generate_date_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "DAY_DIGIT1", "is_accepting": False},
            {"id": "q2", "label": "DAY_DIGIT2", "is_accepting": False},
            {"id": "q3", "label": "SEPARATOR1", "is_accepting": False},
            {"id": "q4", "label": "MONTH_DIGIT1", "is_accepting": False},
            {"id": "q5", "label": "MONTH_DIGIT2", "is_accepting": False},
            {"id": "q6", "label": "SEPARATOR2", "is_accepting": False},
            {"id": "q7", "label": "YEAR", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[0-9]", "to": "q1", "action": "read_day"},
            {"from": "q1", "input": "[0-9]", "to": "q2", "action": "read_day"},
            {"from": "q1", "input": "[-/]", "to": "q3", "action": "read_sep"},
            {"from": "q2", "input": "[-/]", "to": "q3", "action": "read_sep"},
            {"from": "q3", "input": "[0-9]", "to": "q4", "action": "read_month"},
            {"from": "q4", "input": "[0-9]", "to": "q5", "action": "read_month"},
            {"from": "q4", "input": "[-/]", "to": "q6", "action": "read_sep"},
            {"from": "q5", "input": "[-/]", "to": "q6", "action": "read_sep"},
            {"from": "q6", "input": "[0-9]", "to": "q7", "action": "read_year"},
            {"from": "q7", "input": "[0-9]", "to": "q7", "action": "read_year"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q7"],
            "output_action": "format_date_spoken"
        }

    def _generate_time_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "HOUR1", "is_accepting": False},
            {"id": "q2", "label": "HOUR2", "is_accepting": False},
            {"id": "q3", "label": "COLON1", "is_accepting": False},
            {"id": "q4", "label": "MIN1", "is_accepting": False},
            {"id": "q5", "label": "MIN2_ACCEPT", "is_accepting": True},
            {"id": "q6", "label": "COLON2", "is_accepting": False},
            {"id": "q7", "label": "SEC1", "is_accepting": False},
            {"id": "q8", "label": "SEC2_ACCEPT", "is_accepting": True},
            {"id": "q9", "label": "AMPM_ACCEPT", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[0-9]", "to": "q1", "action": "read_hour"},
            {"from": "q1", "input": "[0-9]", "to": "q2", "action": "read_hour"},
            {"from": "q1", "input": ":", "to": "q3", "action": "read_colon"},
            {"from": "q2", "input": ":", "to": "q3", "action": "read_colon"},
            {"from": "q3", "input": "[0-9]", "to": "q4", "action": "read_min"},
            {"from": "q4", "input": "[0-9]", "to": "q5", "action": "read_min"},
            {"from": "q5", "input": ":", "to": "q6", "action": "read_colon"},
            {"from": "q5", "input": " ", "to": "q9", "action": "space"},
            {"from": "q6", "input": "[0-9]", "to": "q7", "action": "read_sec"},
            {"from": "q7", "input": "[0-9]", "to": "q8", "action": "read_sec"},
            {"from": "q9", "input": "A|P", "to": "q9", "action": "read_ampm"},
            {"from": "q9", "input": "M", "to": "q9", "action": "read_ampm"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q5", "q8", "q9"],
            "output_action": "format_time_spoken"
        }

    def _generate_spell_out_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "LETTER", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[A-Za-z]", "to": "q1", "action": "read_letter"},
            {"from": "q1", "input": "[A-Za-z]", "to": "q1", "action": "read_letter"},
            {"from": "q0", "input": "[^A-Za-z]", "to": "q_err", "action": "error"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q1"],
            "output_action": "spell_each_letter"
        }

    def _generate_prefix_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "PREFIX_CHAR", "is_accepting": False},
            {"id": "q2", "label": "PREFIX_COMPLETE", "is_accepting": True},
            {"id": "q3", "label": "DOT_OPTIONAL", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[A-Za-z]", "to": "q1", "action": "read_prefix_char"},
            {"from": "q1", "input": "[A-Za-z/]", "to": "q1", "action": "read_prefix_char"},
            {"from": "q1", "input": "\\b", "to": "q2", "action": "end_prefix"},
            {"from": "q2", "input": "\\.", "to": "q3", "action": "read_dot"},
            {"from": "q1", "input": "\\.", "to": "q3", "action": "read_dot"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q2", "q3"],
            "output_action": "expand_prefix_to_full_word"
        }

    def _generate_unit_dfa(self, rule_type: str) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "INTEGER_PART", "is_accepting": False},
            {"id": "q2", "label": "DECIMAL_DOT", "is_accepting": False},
            {"id": "q3", "label": "DECIMAL_PART", "is_accepting": False},
            {"id": "q4", "label": "SPACE", "is_accepting": False},
            {"id": "q5", "label": "UNIT_CHAR", "is_accepting": False},
            {"id": "q6", "label": "UNIT_COMPLETE", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[0-9]", "to": "q1", "action": "read_number"},
            {"from": "q1", "input": "[0-9]", "to": "q1", "action": "read_number"},
            {"from": "q1", "input": "\\.", "to": "q2", "action": "read_decimal"},
            {"from": "q2", "input": "[0-9]", "to": "q3", "action": "read_decimal_part"},
            {"from": "q3", "input": "[0-9]", "to": "q3", "action": "read_decimal_part"},
            {"from": "q1", "input": " ", "to": "q4", "action": "read_space"},
            {"from": "q3", "input": " ", "to": "q4", "action": "read_space"},
            {"from": "q4", "input": "[A-Za-z]", "to": "q5", "action": "read_unit"},
            {"from": "q5", "input": "[A-Za-z/²³]", "to": "q5", "action": "read_unit"},
            {"from": "q5", "input": "\\b", "to": "q6", "action": "complete_unit"},
            {"from": "q1", "input": "[A-Za-z]", "to": "q5", "action": "read_unit_nospace"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q6", "q5"],
            "output_action": "pronounce_number_with_unit_plural"
        }

    def _generate_currency_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "CURRENCY_SYMBOL", "is_accepting": False},
            {"id": "q2", "label": "INTEGER_PART", "is_accepting": True},
            {"id": "q3", "label": "DECIMAL_DOT", "is_accepting": False},
            {"id": "q4", "label": "CENTS", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[\\$€£₹]", "to": "q1", "action": "read_symbol"},
            {"from": "q0", "input": "[0-9]", "to": "q2", "action": "read_digit_first"},
            {"from": "q1", "input": "[0-9]", "to": "q2", "action": "read_digit"},
            {"from": "q2", "input": "[0-9]", "to": "q2", "action": "read_digit"},
            {"from": "q2", "input": ",", "to": "q2", "action": "skip_comma"},
            {"from": "q2", "input": "\\.", "to": "q3", "action": "read_decimal"},
            {"from": "q3", "input": "[0-9]", "to": "q4", "action": "read_cents"},
            {"from": "q4", "input": "[0-9]", "to": "q4", "action": "read_cents"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q2", "q4"],
            "output_action": "pronounce_currency_amount"
        }

    def _generate_roman_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "ROMAN_CHAR", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[IVXLCDM]", "to": "q1", "action": "read_roman"},
            {"from": "q1", "input": "[IVXLCDM]", "to": "q1", "action": "read_roman"},
            {"from": "q0", "input": "[^IVXLCDM]", "to": "q_err", "action": "error"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q1"],
            "output_action": "convert_roman_to_cardinal"
        }

    def _generate_homophone_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "CONTEXT_SCAN", "is_accepting": False},
            {"id": "q2", "label": "WORD_FOUND", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[A-Za-z]", "to": "q1", "action": "read_word"},
            {"from": "q1", "input": "[A-Za-z]", "to": "q1", "action": "read_word"},
            {"from": "q1", "input": "\\b", "to": "q2", "action": "check_homophone_context"},
            {"from": "q2", "input": ".", "to": "q2", "action": "context_resolved"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q2"],
            "output_action": "use_context_to_select_pronunciation"
        }

    def _generate_temperature_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "NUMBER", "is_accepting": False},
            {"id": "q2", "label": "DEGREE_SYMBOL", "is_accepting": False},
            {"id": "q3", "label": "SCALE", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[0-9]", "to": "q1", "action": "read_number"},
            {"from": "q1", "input": "[0-9.]", "to": "q1", "action": "read_number"},
            {"from": "q1", "input": "°", "to": "q2", "action": "read_degree"},
            {"from": "q2", "input": "[CF]", "to": "q3", "action": "read_scale"},
            {"from": "q1", "input": " ", "to": "q2", "action": "space"},
            {"from": "q2", "input": "[CF]", "to": "q3", "action": "read_scale"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q3"],
            "output_action": "pronounce_temperature"
        }

    def _generate_comma_dfa(self) -> Dict:
        states = [
            {"id": "q0", "label": "START", "is_accepting": False},
            {"id": "q1", "label": "DIGIT_GROUP", "is_accepting": True},
            {"id": "q2", "label": "COMMA", "is_accepting": False},
            {"id": "q3", "label": "AFTER_COMMA", "is_accepting": True},
            {"id": "q_err", "label": "ERROR", "is_accepting": False}
        ]
        transitions = [
            {"from": "q0", "input": "[0-9]", "to": "q1", "action": "read_digit"},
            {"from": "q1", "input": "[0-9]", "to": "q1", "action": "read_digit"},
            {"from": "q1", "input": ",", "to": "q2", "action": "read_comma"},
            {"from": "q2", "input": "[0-9]", "to": "q3", "action": "read_digit_group"},
            {"from": "q3", "input": "[0-9]", "to": "q3", "action": "read_digit_group"},
            {"from": "q3", "input": ",", "to": "q2", "action": "read_comma"}
        ]
        return {
            "states": states, "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q1", "q3"],
            "output_action": "pronounce_with_lakh_thousand"
        }

    def _generate_weekday_dfa(self) -> Dict:
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun",
                "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        states = [{"id": "q0", "label": "START", "is_accepting": False}]
        for i, day in enumerate(days):
            states.append({"id": f"q_day_{i}", "label": f"DAY_{day}", "is_accepting": True})
        states.append({"id": "q_err", "label": "ERROR", "is_accepting": False})
        transitions = [
            {"from": "q0", "input": "Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday",
             "to": "q_day_match", "action": "match_day_abbrev"},
            {"from": "q_day_match", "input": "\\.", "to": "q_day_match", "action": "optional_dot"},
            {"from": "q_day_match", "input": "[a-z]+", "to": "q_day_match", "action": "extend_to_full"},
            {"from": "q0", "input": "[^A-Za-z]", "to": "q_err", "action": "error"}
        ]
        return {
            "states": states[:4], "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q_day_match"],
            "output_action": "expand_day_to_full_name"
        }

    def _generate_month_dfa(self) -> Dict:
        transitions = [
            {"from": "q0", "input": "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec",
             "to": "q1", "action": "match_month"},
            {"from": "q1", "input": "\\.", "to": "q1", "action": "optional_dot"},
            {"from": "q1", "input": "[a-z]+", "to": "q1", "action": "extend_to_full"},
            {"from": "q0", "input": "[^A-Za-z]", "to": "q_err", "action": "error"}
        ]
        return {
            "states": [
                {"id": "q0", "label": "START", "is_accepting": False},
                {"id": "q1", "label": "MONTH_MATCHED", "is_accepting": True},
                {"id": "q_err", "label": "ERROR", "is_accepting": False}
            ],
            "transitions": transitions,
            "initial_state": "q0", "accepting_states": ["q1"],
            "output_action": "expand_month_to_full_name"
        }

    def _generate_date_format_dfa(self) -> Dict:
        return {
            "states": [
                {"id": "q0", "label": "START", "is_accepting": False},
                {"id": "q1", "label": "DAY_WITH_SUFFIX", "is_accepting": False},
                {"id": "q2", "label": "MONTH_NAME", "is_accepting": True},
                {"id": "q3", "label": "YEAR_OPTIONAL", "is_accepting": True},
                {"id": "q_err", "label": "ERROR", "is_accepting": False}
            ],
            "transitions": [
                {"from": "q0", "input": "[0-9]+", "to": "q1", "action": "read_day"},
                {"from": "q1", "input": "st|nd|rd|th", "to": "q1", "action": "read_suffix"},
                {"from": "q1", "input": " ", "to": "q2", "action": "space"},
                {"from": "q2", "input": "[A-Za-z]+", "to": "q2", "action": "read_month_name"},
                {"from": "q2", "input": " ", "to": "q3", "action": "space"},
                {"from": "q3", "input": "[0-9]+", "to": "q3", "action": "read_year"}
            ],
            "initial_state": "q0", "accepting_states": ["q2", "q3"],
            "output_action": "format_date_natural_language"
        }

    def _generate_generic_dfa(self, pattern: str) -> Dict:
        return {
            "states": [
                {"id": "q0", "label": "START", "is_accepting": False},
                {"id": "q1", "label": "MATCHING", "is_accepting": True},
                {"id": "q_err", "label": "ERROR", "is_accepting": False}
            ],
            "transitions": [
                {"from": "q0", "input": f"matches({pattern})", "to": "q1", "action": "apply_pattern"},
                {"from": "q0", "input": f"not_matches({pattern})", "to": "q_err", "action": "error"}
            ],
            "initial_state": "q0", "accepting_states": ["q1"],
            "output_action": "apply_normalization_rule"
        }

    def generate_for_categories(self, language_data: Dict, selected_categories: Optional[List[str]] = None) -> Dict:
        """Generate DFA rules for all or selected categories."""
        result = {
            "language": language_data["language"],
            "language_name": language_data["language_name"],
            "generated_at": __import__('datetime').datetime.now().isoformat(),
            "dfa_rules": {}
        }

        categories = language_data.get("categories", {})
        if selected_categories:
            categories = {k: v for k, v in categories.items() if k in selected_categories}

        for cat_name, cat_data in categories.items():
            result["dfa_rules"][cat_name] = {}
            for subcat_name, subcat_data in cat_data.get("subcategories", {}).items():
                pattern = subcat_data.get("dfa_pattern", ".*")
                rule_type = subcat_data.get("rule_type", "generic")
                dfa = self.generate_dfa_for_pattern(pattern, cat_name, subcat_name, rule_type)
                result["dfa_rules"][cat_name][subcat_name] = dfa

        return result