import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_application_root():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200

    assert "text/html" in response.headers["content-type"]

    body = response.text

    assert "Mwalimu AI" in body
    assert "auth.js" in body
