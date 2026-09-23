import pytest
from pydantic import ValidationError
from backend.app.api.schemas.exploration import ExplorationCreate
from backend.app.database.models.models import Application, Environment, EnvironmentType, ExplorationRun, ExplorationStatus
from backend.app.database.repositories.exploration_repo import ExplorationRepository
from backend.app.database.repositories.application_repo import ApplicationRepository
from backend.app.services.exploration_service import ExplorationService

def test_valid_http_url():
    data = ExplorationCreate(
        application_id=1,
        environment_id=1,
        target_url="http://127.0.0.1:3000"
    )
    assert data.target_url == "http://127.0.0.1:3000"


def test_valid_https_url():
    data = ExplorationCreate(
        application_id=1,
        environment_id=1,
        target_url="https://example.com/crm/dashboard"
    )
    assert data.target_url == "https://example.com/crm/dashboard"


def test_invalid_url():
    with pytest.raises(ValidationError) as exc_info:
        ExplorationCreate(
            application_id=1,
            environment_id=1,
            target_url="not-a-valid-url-without-scheme"
        )
    assert "must use http or https protocol" in str(exc_info.value).lower()


def test_empty_url():
    with pytest.raises(ValidationError) as exc_info:
        ExplorationCreate(
            application_id=1,
            environment_id=1,
            target_url=""
        )
    assert "cannot be empty" in str(exc_info.value).lower()

    with pytest.raises(ValidationError) as exc_info2:
        ExplorationCreate(
            application_id=1,
            environment_id=1,
            target_url="    "
        )
    assert "cannot be empty" in str(exc_info2.value).lower()


def test_unsupported_protocol_ftp():
    with pytest.raises(ValidationError) as exc_info:
        ExplorationCreate(
            application_id=1,
            environment_id=1,
            target_url="ftp://ftp.example.com/download"
        )
    assert "must use http or https protocol" in str(exc_info.value).lower()


def test_unsupported_protocol_javascript():
    with pytest.raises(ValidationError) as exc_info:
        ExplorationCreate(
            application_id=1,
            environment_id=1,
            target_url="javascript:alert(1)"
        )
    assert "must use http or https protocol" in str(exc_info.value).lower()


def test_unsupported_protocol_file():
    with pytest.raises(ValidationError) as exc_info:
        ExplorationCreate(
            application_id=1,
            environment_id=1,
            target_url="file:///etc/passwd"
        )
    assert "must use http or https protocol" in str(exc_info.value).lower()


def test_api_validation_via_testclient(client):
    # 1. Valid HTTP URL
    res_http = client.post("/api/explorations", json={
        "application_id": 2,
        "environment_id": 1,
        "target_url": "http://127.0.0.1:3000"
    })
    assert res_http.status_code == 201
    assert res_http.json()["target_url"] == "http://127.0.0.1:3000"

    # 2. Valid HTTPS URL
    res_https = client.post("/api/explorations", json={
        "application_id": 2,
        "environment_id": 1,
        "target_url": "https://example.com"
    })
    assert res_https.status_code == 201
    assert res_https.json()["target_url"] == "https://example.com"

    # 3. Invalid URL -> 422
    res_invalid = client.post("/api/explorations", json={
        "application_id": 2,
        "environment_id": 1,
        "target_url": "invalid_url_string"
    })
    assert res_invalid.status_code == 422

    # 4. Empty URL -> 422
    res_empty = client.post("/api/explorations", json={
        "application_id": 2,
        "environment_id": 1,
        "target_url": ""
    })
    assert res_empty.status_code == 422

    # 5. Unsupported Protocol (ftp) -> 422
    res_ftp = client.post("/api/explorations", json={
        "application_id": 2,
        "environment_id": 1,
        "target_url": "ftp://files.example.com"
    })
    assert res_ftp.status_code == 422


def test_custom_target_url_precedence_over_environment(db_session):
    app_repo = ApplicationRepository(db_session)
    expl_repo = ExplorationRepository(db_session)

    # Predefined environment has base_url http://example-default.local
    app = app_repo.get_by_id(2)
    env = app_repo.get_environment_by_id(1)

    # 1. Run with custom target_url
    custom_run = expl_repo.create_run(ExplorationCreate(
        application_id=app.id,
        environment_id=env.id,
        target_url="http://127.0.0.1:3000/custom"
    ))
    assert custom_run.target_url == "http://127.0.0.1:3000/custom"

    # 2. Run without custom target_url (should be None until exploration resolves it)
    default_run = expl_repo.create_run(ExplorationCreate(
        application_id=app.id,
        environment_id=env.id,
        target_url=None
    ))
    assert default_run.target_url is None
