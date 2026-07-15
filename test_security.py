import requests
import asyncio
import websockets

BASE_URL = "http://localhost:8000"

def get_manual_token(username: str, roles: list) -> str:
    print(f"\n[1] Requesting Manual Token for {username} with roles: {roles}")
    response = requests.post(
        f"{BASE_URL}/auth/manual-token", 
        json={"username": username, "roles": roles}
    )
    token = response.json()["access_token"]
    print(f"    Token Generated: {token[:20]}...\n")
    return token

def test_rest_api_security(token: str):
    print("[2] Testing REST API /ask (Requires 'listener' role)")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/meetings/test_meeting/ask",
        json={"question": "What happened?"},
        headers=headers
    )
    if response.status_code == 200:
        print("    ✅ SUCCESS: Agent answered (listener role verified).")
    else:
        print(f"    ❌ BLOCKED: {response.status_code} - {response.json()}")

async def test_websocket_security(token: str):
    print("\n[3] Testing WebSocket /ws/meeting-stream (Requires 'speaker' role)")
    ws_url = f"ws://localhost:8000/ws/meeting-stream?token={token}"
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("    ✅ SUCCESS: Connected to WebSocket! You can speak.")
            await ws.close()
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"    ❌ BLOCKED: WebSocket closed with code {e.code} (Missing 'speaker' role).")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"    ❌ BLOCKED: HTTP Error {e.status_code}.")

async def main():
    print("====================================")
    print("Testing User A (Listener Only)")
    print("====================================")
    token_a = get_manual_token("ListenerUser", ["listener"])
    test_rest_api_security(token_a)
    await test_websocket_security(token_a)
    
    print("\n====================================")
    print("Testing User B (Speaker Only)")
    print("====================================")
    token_b = get_manual_token("SpeakerUser", ["speaker"])
    test_rest_api_security(token_b) # Should fail
    await test_websocket_security(token_b) # Should succeed

if __name__ == "__main__":
    asyncio.run(main())
