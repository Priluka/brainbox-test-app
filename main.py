import os, json, requests, time

api_url = os.environ.get("BRAINBOX_API_URL", "")
api_token = os.environ.get("BRAINBOX_API_TOKEN", "")
session_id = os.environ.get("BRAINBOX_SESSION_ID", "")
credentials = json.loads(os.environ.get("BRAINBOX_CREDENTIALS", "{}"))

print(f"Session: {session_id}")
print(f"API URL: {api_url}")
print(f"Models: {[m['name'] for m in credentials.get('models', [])]}")
print(f"Tools: {[t['name'] for t in credentials.get('tools', [])]}")

if api_url and api_token and session_id:
    headers = {"Content-Type": "application/json", "x-brainbox-token": api_token}

    # Send a bubble message
    requests.post(f"{api_url}/sessions/{session_id}/messages", json={
        "message": {"text": "Hello from Brainbox test container!", "displayType": "bubble"}
    }, headers=headers)

    time.sleep(1)

    # Send completion with output
    requests.post(f"{api_url}/sessions/{session_id}/complete", json={
        "output": {"status": "ok", "message": "Test container completed successfully"}
    }, headers=headers)

    print("Messages sent, session completed.")
else:
    print("Missing env vars — running in standalone mode.")

print("Done.")
