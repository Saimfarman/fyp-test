import os

import pytest

os.environ["APP_ENV"] = "test"

from app import create_app


@pytest.mark.asyncio
async def test_liveness():
    app = create_app()
    client = app.test_client()
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert await response.get_json() == {"status": "ok"}
