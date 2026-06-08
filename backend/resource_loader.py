import json
import os


class ResourceLoader:

    def __init__(self):
        # backend/resources/languages/
        self.base_path = os.path.join(
            os.path.dirname(__file__),
            "resources",
            "languages"
        )

    def load_language(self, language_code):
        """
        Load language JSON file dynamically.
        Example:
            en -> en.json
        """

        file_path = os.path.join(
            self.base_path,
            f"{language_code}.json"
        )

        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Language file not found: {language_code}"
            )

        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def get_categories(self, language_code):
        """
        Return all categories
        """

        data = self.load_language(language_code)

        return data.get("categories", {})

    def get_ssml_templates(self, language_code):
        """
        Return SSML templates
        """

        data = self.load_language(language_code)

        return data.get("ssml_templates", {})

    def get_subcategories(self, language_code, category):
        """
        Return subcategories inside a category
        """

        categories = self.get_categories(language_code)

        if category not in categories:
            return {}

        return categories[category].get("subcategories", {})