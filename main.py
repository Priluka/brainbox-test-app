import os, json, requests, time

# --- Brainbox communication (lightweight, no SDK dependency) ---
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
                    return msgs[-1].get("text", "")
        except:
            time.sleep(1)
    return None

def complete(output=None):
    requests.post(f"{base}/complete", json={"output": output} if output else {}, headers=headers, timeout=10)

# --- CrewAI ---
from crewai import Agent, Task, Crew, LLM

# Read API key from env var (user sets this in CODE app config)
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
model_name = os.environ.get("LLM_MODEL", "anthropic/claude-haiku-4-5")

if not api_key:
    send("Error: ANTHROPIC_API_KEY env var not set. Add it in the app's Environment Variables.")
    complete(output={"error": "No API key"})
    exit(1)

llm = LLM(model=model_name, api_key=api_key)

send("Hi! I'm a CrewAI research bot. What topic should I research?")

topic = wait_for_message(timeout=120)
if not topic:
    send("No topic received. Ending session.")
    complete()
    exit(0)

send(f"Researching '{topic}'... This may take a moment.")

# Create crew
researcher = Agent(
    role="Senior Researcher",
    goal=f"Find the most important and relevant information about {topic}",
    backstory="You are an expert researcher with deep knowledge across many fields. You provide concise, accurate summaries.",
    llm=llm,
    verbose=False,
)

research_task = Task(
    description=f"Research the topic: {topic}. Provide a clear, concise summary with key facts and insights. Keep it under 200 words.",
    expected_output="A concise research summary with key facts",
    agent=researcher,
)

crew = Crew(
    agents=[researcher],
    tasks=[research_task],
    verbose=False,
)

try:
    result = crew.kickoff()
    send(str(result), display_type="final")
    complete(output={"topic": topic, "result": str(result)})
except Exception as e:
    send(f"Crew failed: {str(e)}")
    complete(output={"error": str(e)})

print("Done.")
