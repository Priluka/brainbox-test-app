import os, json, requests, time

api_url = os.environ.get("BRAINBOX_API_URL", "")
api_token = os.environ.get("BRAINBOX_API_TOKEN", "")
session_id = os.environ.get("BRAINBOX_SESSION_ID", "")

headers = {"Content-Type": "application/json", "x-brainbox-token": api_token}
base = f"{api_url}/sessions/{session_id}"

def send(text, display_type="bubble"):
    requests.post(f"{base}/messages", json={
        "message": {"text": text, "displayType": display_type}
    }, headers=headers, timeout=10)

def wait_for_message(timeout=120):
    after = int(time.time() * 1000)
    deadline = time.time() + timeout
    while time.time() < deadline:
        wait = min(30, max(1, int(deadline - time.time())))
        try:
            resp = requests.get(f"{base}/messages/pending",
                params={"after": after, "wait": wait},
                headers=headers, timeout=wait + 5)
            if resp.ok:
                msgs = resp.json().get("messages", [])
                if msgs:
                    after = msgs[-1].get("ts", after)
                    return msgs[-1].get("text", "")
        except requests.exceptions.Timeout:
            continue
        except Exception:
            time.sleep(1)
    return None

def complete(output=None):
    body = {"output": output} if output else {}
    requests.post(f"{base}/complete", json=body, headers=headers, timeout=10)

# --- Interactive test ---
print(f"Session: {session_id}")
print(f"API URL: {api_url}")

send("Hello! I'm an interactive test bot. Ask me anything (type 'quit' to end).")

for i in range(10):
    print(f"Waiting for message {i+1}...")
    msg = wait_for_message(timeout=120)
    
    if not msg:
        send("No response received. Ending session.")
        break
    
    print(f"Got: {msg}")
    
    if msg.lower().strip() == "quit":
        send("Goodbye! Session ending.")
        break
    
    # Echo back with some processing
    response = f"You said: '{msg}' (message #{i+1}, {len(msg)} chars)"
    send(response)

complete(output={"status": "ok", "messages_exchanged": i + 1})
print("Done.")
