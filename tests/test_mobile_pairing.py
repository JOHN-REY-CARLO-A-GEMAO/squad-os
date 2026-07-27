import pytest
from fastapi.testclient import TestClient
from squad_os.api.main import app
from squad_os.database.session import init_db

@pytest.mark.asyncio
async def test_mobile_pairing_endpoints():
    await init_db()
    client = TestClient(app)

    # 1. Handshake
    res = client.post("/api/v1/handshake", json={
        "client_version": "2.0.0",
        "capabilities": ["qr_pairing"]
    })
    assert res.status_code == 200
    data = res.json()
    assert data["server_version"] == "2.0.4"
    assert data["negotiated_capabilities"]["qr_pairing"] is True

    # 2. Pair Request
    pair_res = client.post("/api/v1/pair/request", json={
        "pairing_url": "squados://pair?host=localhost&port=8000&nonce=test_nonce",
        "ticket_version": 1,
        "nonce": "test_nonce",
        "device_id": "test_device_id"
    })
    assert pair_res.status_code == 200
    assert pair_res.json()["status"] == "SUCCESS"

    # 3. Pair Token (Awaiting Approval)
    token_res = client.get("/api/v1/pair/token?device_id=test_device_id&nonce=test_nonce")
    assert token_res.status_code == 202
    assert token_res.json()["detail"] == "AWAITING_APPROVAL"
