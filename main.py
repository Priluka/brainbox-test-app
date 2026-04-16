import os, json, requests, time

# --- Brainbox communication ---
api_url = os.environ.get("BRAINBOX_API_URL", "")
api_token = os.environ.get("BRAINBOX_API_TOKEN", "")
session_id = os.environ.get("BRAINBOX_SESSION_ID", "")
headers = {"Content-Type": "application/json", "x-brainbox-token": api_token}
base = f"{api_url}/sessions/{session_id}"

def send(text, display_type="bubble"):
    requests.post(f"{base}/messages", json={
        "message": {"text": text, "displayType": display_type}
    }, headers=headers, timeout=10)

def wait_for_message(timeout=180):
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
                    return msgs[-1].get("text", "")
        except:
            time.sleep(1)
    return None

def complete(output=None):
    requests.post(f"{base}/complete", json={"output": output} if output else {}, headers=headers, timeout=10)

# --- CrewAI ---
from crewai import Agent, Task, Crew, LLM

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    send("Error: ANTHROPIC_API_KEY not set.")
    complete(output={"error": "No API key"})
    exit(1)

llm = LLM(model="anthropic/claude-haiku-4-5", api_key=api_key)

# --- Multi-turn conversation ---
send("Hi! I'm a research assistant powered by CrewAI + Claude.\n\nWhat topic should I research?")

topic = wait_for_message()
if not topic:
    send("No response. Goodbye!")
    complete()
    exit(0)

send(f"Researching **{topic}**... one moment.")

# First research
researcher = Agent(
    role="Senior Researcher",
    goal=f"Research {topic} thoroughly",
    backstory="Expert researcher providing concise, accurate summaries.",
    llm=llm,
    verbose=False,
)

task = Task(
    description=f"Research '{topic}'. Provide a clear summary with key facts. Under 200 words.",
    expected_output="Concise research summary",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task], verbose=False)

try:
    result = crew.kickoff()
    send(str(result), display_type="final")
except Exception as e:
    send(f"Research failed: {e}")
    complete(output={"error": str(e)})
    exit(1)

# Ask for feedback
send("Would you like me to:\n1. **Dig deeper** into a specific aspect\n2. **Research a new topic**\n3. **End session** (type 'quit')")

while True:
    response = wait_for_message()
    if not response:
        send("No response. Ending session.")
        break

    if response.lower().strip() in ("quit", "exit", "end", "3"):
        send("Thanks for using the research assistant! Goodbye.")
        break

    if response.strip() == "2":
        send("What new topic should I research?")
        topic = wait_for_message()
        if not topic:
            break
        send(f"Researching **{topic}**...")
    else:
        # Dig deeper or follow-up
        topic = f"{topic} — specifically: {response}"
        send(f"Digging deeper into: **{response}**...")

    task = Task(
        description=f"Research '{topic}'. Provide a clear summary. Under 200 words.",
        expected_output="Concise research summary",
        agent=researcher,
    )
    crew = Crew(agents=[researcher], tasks=[task], verbose=False)

    try:
        result = crew.kickoff()
        send(str(result), display_type="final")
        send("What next?\n1. **Dig deeper**\n2. **New topic**\n3. **Quit**")
    except Exception as e:
        send(f"Research failed: {e}")
        break

complete(output={"status": "ok", "last_topic": topic})
print("Done.")
