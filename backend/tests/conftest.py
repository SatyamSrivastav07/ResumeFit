import pytest
from mongomock_motor import AsyncMongoMockClient

from app.dependencies.persistence import require_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database():
    client = AsyncMongoMockClient()
    database = client["resumefit_test"]
    app.dependency_overrides[require_database] = lambda: database
    yield database
    app.dependency_overrides.pop(require_database, None)
    client.close()
