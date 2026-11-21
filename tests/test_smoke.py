def test_settings_load_without_env(settings):
    assert settings.SECRET_KEY
    assert "testserver" in settings.ALLOWED_HOSTS
