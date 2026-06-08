"""
Flask Backend for TTS Text Normalization Rule Generation Framework
"""

import os
import json
import io
import zipfile
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS

from language_loader import LanguageLoader
from dfa_generator import DFAGenerator
from normalization_generator import NormalizationRuleGenerator
from ssml_generator import SSMLGenerator
from classifier import CategoryClassifier
from normalizer_engine import NormalizerEngine

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static')
)
CORS(app)

# Initialize components
loader = LanguageLoader()
dfa_gen = DFAGenerator()
norm_gen = NormalizationRuleGenerator()
ssml_gen = SSMLGenerator()
classifier = CategoryClassifier()
normalizer = NormalizerEngine()


# ─────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────

def _build_download_bundle(lang_data: dict, categories: list) -> dict:
    """Build complete generation bundle for given language + categories."""
    dfa_rules     = dfa_gen.generate_for_categories(lang_data, categories or None)
    norm_rules    = norm_gen.generate_all_rules(lang_data, categories or None)
    ssml_rules    = ssml_gen.generate_ssml_rules(lang_data, categories or None)
    return {
        "metadata": {
            "language":      lang_data["language"],
            "language_name": lang_data["language_name"],
            "generated_at":  datetime.now().isoformat(),
            "categories":    categories or list(lang_data.get("categories", {}).keys()),
            "mode":          "rule_generation"
        },
        "dfa_rules":            dfa_rules,
        "normalization_rules":  norm_rules,
        "ssml_rules":           ssml_rules
    }


# ─────────────────────────────────────────────
# Routes – Pages
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─────────────────────────────────────────────
# Routes – API
# ─────────────────────────────────────────────

@app.route("/api/languages", methods=["GET"])
def get_languages():
    """Return available languages."""
    try:
        languages = loader.get_available_languages()
        return jsonify({"success": True, "languages": languages})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/categories/<lang_code>", methods=["GET"])
def get_categories(lang_code: str):
    """Return categories for a language."""
    try:
        categories = loader.get_categories_for_language(lang_code)
        return jsonify({"success": True, "categories": categories})
    except FileNotFoundError:
        return jsonify({"success": False, "error": f"Language '{lang_code}' not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def generate_rules():
    """
    MODE 1 – Rule Generation Mode.
    Body: { "language": "en", "categories": ["NUMBER", "DATE"] }
    If categories is empty/omitted → generate for ALL categories.
    """
    try:
        body       = request.get_json(force=True)
        lang_code  = body.get("language", "").strip()
        categories = body.get("categories", [])   # [] means all

        if not lang_code:
            return jsonify({"success": False, "error": "language is required"}), 400

        lang_data = loader.load_language(lang_code)

        # Filter categories list
        if categories:
            available = set(lang_data.get("categories", {}).keys())
            categories = [c for c in categories if c in available]

        bundle = _build_download_bundle(lang_data, categories)

        # ── summary for the UI ──
        dfa_count  = sum(len(v) for v in bundle["dfa_rules"]["dfa_rules"].items() if isinstance(v, dict))
        norm_count = len(bundle["normalization_rules"]["normalization_rules"])
        ssml_count = len(bundle["ssml_rules"]["ssml_rules"])

        return jsonify({
            "success":     True,
            "mode":        "rule_generation",
            "language":    lang_data["language_name"],
            "categories":  categories or list(lang_data.get("categories", {}).keys()),
            "summary": {
                "dfa_rules_count":            sum(
                    len(v) for v in bundle["dfa_rules"]["dfa_rules"].values()
                ),
                "normalization_rules_count":  norm_count,
                "ssml_rules_count":           ssml_count,
                "ssml_examples_count":        len(bundle["ssml_rules"]["ssml_examples"])
            },
            "dfa_rules":           bundle["dfa_rules"],
            "normalization_rules": bundle["normalization_rules"],
            "ssml_rules":          bundle["ssml_rules"]
        })

    except FileNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/detect", methods=["POST"])
def detect_and_generate():
    """
    MODE 2 – Smart Detection Mode.
    Body: { "text": "I live in 560083", "language": "en" }
    """
    try:
        body      = request.get_json(force=True)
        text      = body.get("text", "").strip()
        lang_code = body.get("language", "en").strip()

        if not text:
            return jsonify({"success": False, "error": "text is required"}), 400

        lang_data = loader.load_language(lang_code)

        # Classify with unified DFA+ML engine
        detection = classifier.classify(text, lang_data=lang_data)
        detected_category = detection["detected_category"]
        detected_subcategory = detection["detected_subcategory"]
        rule_type = detection["rule_type"]
        matched_token = detection["matched_token"]

        # Normalize the text using the normalizer engine
        normalized_output = normalizer.normalize(
            lang_data, detected_category, detected_subcategory, rule_type, matched_token
        )

        # Generate rules only for the detected category
        cats_to_generate = [detected_category]
        # Handle sub-mapping: PINCODE lives as a top-level category in some langs
        available_cats = set(lang_data.get("categories", {}).keys())
        if detected_category not in available_cats:
            # Fall back to NUMBER for PIN/special
            if detected_category in ("PINCODE",):
                cats_to_generate = ["NUMBER"]
            else:
                cats_to_generate = list(available_cats)[:2]

        bundle = _build_download_bundle(lang_data, cats_to_generate)

        return jsonify({
            "success":  True,
            "mode":     "smart_detection",
            "language": lang_data["language_name"],
            "input_text": text,
            "normalized_text": text.replace(matched_token, normalized_output),
            "normalized_token": normalized_output,
            "detection": {
                "detected_category":    detection["detected_category"],
                "detected_subcategory": detection["detected_subcategory"],
                "rule_type":            detection["rule_type"],
                "matched_token":        detection["matched_token"],
                "confidence":           round(detection["confidence"], 3),
                "reasoning":            detection["reasoning"],
                "source":               detection.get("source", "ML"),
                "all_candidates":       detection["all_candidates"]
            },
            "generated_for_categories": cats_to_generate,
            "summary": {
                "dfa_rules_count": sum(
                    len(v) for v in bundle["dfa_rules"]["dfa_rules"].values()
                ),
                "normalization_rules_count": len(bundle["normalization_rules"]["normalization_rules"]),
                "ssml_rules_count":          len(bundle["ssml_rules"]["ssml_rules"])
            },
            "dfa_rules":           bundle["dfa_rules"],
            "normalization_rules": bundle["normalization_rules"],
            "ssml_rules":          bundle["ssml_rules"]
        })

    except FileNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/download", methods=["POST"])
def download_rules():
    """
    Download generated rules as a ZIP containing three JSON files.
    Body: same as /api/generate  OR  { ...generate payload..., "bundle": <pre-built bundle> }
    """
    try:
        body      = request.get_json(force=True)
        lang_code = body.get("language", "").strip()
        categories = body.get("categories", [])

        if not lang_code:
            return jsonify({"success": False, "error": "language is required"}), 400

        lang_data = loader.load_language(lang_code)
        bundle    = _build_download_bundle(lang_data, categories or None)

        # Build in-memory ZIP
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                f"{lang_code}_dfa_rules.json",
                json.dumps(bundle["dfa_rules"], indent=2, ensure_ascii=False)
            )
            zf.writestr(
                f"{lang_code}_normalization_rules.json",
                json.dumps(bundle["normalization_rules"], indent=2, ensure_ascii=False)
            )
            zf.writestr(
                f"{lang_code}_ssml_rules.json",
                json.dumps(bundle["ssml_rules"], indent=2, ensure_ascii=False)
            )
            zf.writestr(
                "README.txt",
                f"TTS Text Normalization Rules\n"
                f"Language : {lang_data['language_name']} ({lang_code})\n"
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Files:\n"
                f"  {lang_code}_dfa_rules.json          - DFA state machines\n"
                f"  {lang_code}_normalization_rules.json - Normalization step rules\n"
                f"  {lang_code}_ssml_rules.json          - SSML markup templates\n"
            )

        buf.seek(0)
        fname = f"{lang_code}_tts_rules_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        return send_file(
            buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name=fname
        )

    except FileNotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("\n🚀 TTS Text Normalization Framework")
    print("   Backend running at: http://127.0.0.1:5000")
    print("   Open your browser at http://127.0.0.1:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)