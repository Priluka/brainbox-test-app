"""
Comprehensive Brainbox CODE app test.
Tests: long polling, multi-turn chat, CrewAI crew, human feedback, multiple agents.
"""
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

# --- Setup ---
from crewai import Agent, Task, Crew, LLM

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    send("Error: ANTHROPIC_API_KEY not set.")
    complete(output={"error": "No API key"})
    exit(1)

llm = LLM(model="anthropic/claude-haiku-4-5", api_key=api_key)

# --- Agents ---
researcher = Agent(
    role="Senior Researcher",
    goal="Find accurate, relevant information on any topic",
    backstory="You are an expert researcher. You provide concise, well-structured summaries with key facts.",
    llm=llm,
    verbose=False,
)

critic = Agent(
    role="Quality Reviewer",
    goal="Review research for accuracy and completeness",
    backstory="You are a critical reviewer. You identify gaps, suggest improvements, and rate quality.",
    llm=llm,
    verbose=False,
)

writer = Agent(
    role="Content Writer",
    goal="Create polished, well-written final content",
    backstory="You are a skilled writer. You take raw research and feedback to produce clear, engaging content.",
    llm=llm,
    verbose=False,
)

# --- Start conversation ---
send("Welcome! I'm a multi-agent research team powered by **CrewAI + Claude**.\n\nI have 3 agents:\n- **Researcher** — finds information\n- **Critic** — reviews quality\n- **Writer** — produces final content\n\nWhat topic should we research?")

topic = wait_for_message()
if not topic:
    send("No topic received. Goodbye!")
    complete()
    exit(0)

# === STEP 1: Research ===
send(f"**Step 1/3: Researching** '{topic}'...")

research_task = Task(
    description=f"Research the topic: '{topic}'. Provide key facts, recent developments, and important context. Be thorough but concise (under 200 words).",
    expected_output="A structured research summary with key facts",
    agent=researcher,
)

crew1 = Crew(agents=[researcher], tasks=[research_task], verbose=False)
try:
    research_result = crew1.kickoff()
    send(str(research_result), display_type="final")
except Exception as e:
    send(f"Research failed: {e}")
    complete(output={"error": str(e)})
    exit(1)

# === STEP 2: Human review ===
send("**Step 2/3: Your review**\n\nPlease review the research above. You can:\n- Type **'ok'** to approve and proceed to final draft\n- Type **feedback** to improve it (e.g. 'add more about costs')\n- Type **'quit'** to end")

feedback = wait_for_message()
if not feedback or feedback.lower().strip() in ("quit", "exit"):
    send("Session ended. Thanks!")
    complete(output={"topic": topic, "result": str(research_result)})
    exit(0)

# === STEP 3: Critique + Final draft ===
if feedback.lower().strip() == "ok":
    send("**Step 3/3: Writing final draft**...")
    extra_instructions = "The research was approved as-is."
else:
    send(f"**Step 3/3: Revising** based on your feedback: '{feedback}'...")
    extra_instructions = f"Human feedback: {feedback}. Address this in the review and final draft."

# Critic reviews
critique_task = Task(
    description=f"Review this research about '{topic}':\n\n{research_result}\n\n{extra_instructions}\n\nProvide a brief quality assessment and suggestions (under 100 words).",
    expected_output="Quality assessment with suggestions",
    agent=critic,
)

# Writer creates final version
write_task = Task(
    description=f"Using the research and review, write a polished final summary about '{topic}'. Make it clear, engaging, and well-structured. Under 250 words. Use markdown formatting.",
    expected_output="A polished, well-formatted summary",
    agent=writer,
    context=[critique_task],
)

crew2 = Crew(agents=[critic, writer], tasks=[critique_task, write_task], verbose=False)
try:
    final_result = crew2.kickoff()
    send(str(final_result), display_type="final")
except Exception as e:
    send(f"Final draft failed: {e}")
    complete(output={"error": str(e)})
    exit(1)

# === Follow-up ===
send("Done! Would you like to:\n- **Research another topic** (type a new topic)\n- **End session** (type 'quit')")

followup = wait_for_message()
if followup and followup.lower().strip() not in ("quit", "exit", "end"):
    topic = followup
    send(f"Quick research on **{topic}**...")

    quick_task = Task(
        description=f"Quick research on '{topic}'. Key facts only, under 150 words.",
        expected_output="Brief summary",
        agent=researcher,
    )
    crew3 = Crew(agents=[researcher], tasks=[quick_task], verbose=False)
    try:
        quick_result = crew3.kickoff()
        send(str(quick_result), display_type="final")
    except Exception as e:
        send(f"Failed: {e}")

send("Thanks for using the research team! Session complete.")
complete(output={"topic": topic, "status": "completed"})
print("Done.")
