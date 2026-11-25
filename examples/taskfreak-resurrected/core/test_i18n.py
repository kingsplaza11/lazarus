from django.conf import settings
from django.test import TestCase
from django.utils import translation


class I18nTests(TestCase):
    def test_default_language_is_english(self):
        assert settings.LANGUAGE_CODE == "en"
        r = self.client.get("/login/")
        self.assertContains(r, "Forgot your password?")
        self.assertContains(r, '<html lang="en">')

    def test_languages_include_known_codes(self):
        codes = {c for c, _ in settings.LANGUAGES}
        assert {"ca", "zh-hans", "cs", "da", "de", "en", "es", "fr"} <= codes

    def test_accept_language_translates(self):
        r = self.client.get("/login/", headers={"accept-language": "fr"})
        self.assertContains(r, "Mot de passe oublié")

    def test_language_selector_switches_and_persists(self):
        r = self.client.post("/i18n/setlang/", {"language": "de", "next": "/login/"})
        self.assertRedirects(r, "/login/", fetch_redirect_response=False)
        r = self.client.get("/login/")
        self.assertContains(r, "Passwort vergessen?")
        self.assertContains(r, '<option value="de" selected>')

    def test_selector_lists_all_languages(self):
        r = self.client.get("/login/")
        for code, _ in settings.LANGUAGES:
            self.assertContains(r, f'<option value="{code}"')

    def test_every_locale_has_compiled_catalog(self):
        for code, _ in settings.LANGUAGES:
            if code == "en":
                continue
            with translation.override(code):
                assert translation.gettext("Logout") != "Logout", code
