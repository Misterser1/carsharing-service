from app.core.config import Settings


def test_defaults():
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"
    assert settings.http_port == 8000
    assert settings.docs_enabled


def test_reads_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("HTTP_PORT", "8080")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")

    settings = Settings(_env_file=None)

    assert settings.http_port == 8080
    assert settings.cors_origins == ["http://a.test", "http://b.test"]
    assert not settings.docs_enabled


def test_reads_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text('APP_NAME="From File API"\nLOG_LEVEL=DEBUG\n', encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "From File API"
    assert settings.log_level == "DEBUG"


def test_environment_overrides_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("HTTP_PORT=9000\n", encoding="utf-8")
    monkeypatch.setenv("HTTP_PORT", "9100")

    assert Settings(_env_file=env_file).http_port == 9100


def test_example_file_is_valid():
    # .env.example должен читаться без ошибок — это шаблон для всех окружений
    settings = Settings(_env_file=".env.example")
    assert settings.app_name == "Carsharing Rental API"
