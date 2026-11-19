import pytest

from app.core.config import ConfigError, Settings, load_settings
from tests.conftest import DB_ENV

DB_VARS = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME", "DB_MAX_CONNS"]


@pytest.fixture(autouse=True)
def clean_db_env(monkeypatch):
    # переменные DB_* из окружения разработчика не должны влиять на тесты
    for name in DB_VARS:
        monkeypatch.delenv(name, raising=False)


def test_defaults():
    settings = Settings(_env_file=None, **DB_ENV)
    assert settings.app_env == "development"
    assert settings.http_port == 8080
    assert settings.db_port == 5432
    assert settings.db_max_conns == 10
    assert settings.docs_enabled


def test_reads_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("HTTP_PORT", "9000")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    monkeypatch.setenv("DB_HOST", "db")
    monkeypatch.setenv("DB_USER", "app_user")
    monkeypatch.setenv("DB_PASSWORD", "secret123")
    monkeypatch.setenv("DB_NAME", "carsharing")
    monkeypatch.setenv("DB_MAX_CONNS", "5")

    settings = Settings(_env_file=None)

    assert settings.http_port == 9000
    assert settings.cors_origins == ["http://a.test", "http://b.test"]
    assert not settings.docs_enabled
    assert settings.db_host == "db"
    assert settings.db_max_conns == 5


def test_reads_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        'APP_NAME="From File API"\nLOG_LEVEL=DEBUG\n'
        "DB_HOST=db\nDB_USER=u\nDB_PASSWORD=p\nDB_NAME=n\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "From File API"
    assert settings.log_level == "DEBUG"


def test_environment_overrides_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("HTTP_PORT=9000\n", encoding="utf-8")
    monkeypatch.setenv("HTTP_PORT", "9100")

    assert Settings(_env_file=env_file, **DB_ENV).http_port == 9100


def test_example_file_is_valid():
    # .env.example должен читаться без ошибок — это шаблон для всех окружений
    settings = Settings(_env_file=".env.example")
    assert settings.app_name == "Carsharing Rental API"
    assert settings.db_user == "app_user"


def test_missing_db_variables_stop_startup():
    with pytest.raises(ConfigError) as exc:
        load_settings(_env_file=None)

    message = str(exc.value)
    assert "не заданы обязательные переменные окружения" in message
    for name in ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]:
        assert name in message


def test_empty_variable_counts_as_not_set(monkeypatch):
    monkeypatch.setenv("DB_HOST", "")

    with pytest.raises(ConfigError, match="DB_HOST"):
        load_settings(_env_file=None, db_user="u", db_password="p", db_name="n")


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_invalid_max_conns(monkeypatch, value):
    monkeypatch.setenv("DB_MAX_CONNS", value)

    with pytest.raises(ConfigError, match="некорректные значения: DB_MAX_CONNS"):
        load_settings(_env_file=None, **DB_ENV)


def test_password_is_hidden():
    settings = Settings(_env_file=None, **DB_ENV)

    assert "test_password" not in repr(settings)
    assert settings.db_password.get_secret_value() == "test_password"
