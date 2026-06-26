# AgentVerse — Chaotic Indian Metropolis Simulation 🇮🇳

Welcome to **AgentVerse**, a living, breathing simulation of a chaotic Indian metropolis (inspired by the daily hustle of Bangalore, Delhi, and Mumbai). 

Here, 100 autonomous agents—ranging from moonlighting IT developers and local Netas to auto-rickshaw union presidents and cutting-chai tapri owners—live their lives, manage their cash flows, navigate the notorious Silk Board traffic, and form friendships or rivalries in a closed-loop microeconomy.

Everything is event-sourced, meaning you can use the **Time Machine** slider on the dashboard to rewind and replay the city's history step-by-step.

---

## 🌆 What's Different? (The Indian Metropolis Context)

We moved away from generic cyberpunk tropes to build a simulation that feels like a real, chaotic Indian city:

* **Localized Factions & Occupations**:
  * 🏛️ **Authority & Netas** (*formerly Corp*): Corporators, RTO Inspectors, and bureaucrats who collect municipal dues and launch encroachment drives.
  * 💻 **IT & Side-Hustlers** (*formerly Hacker*): Software engineers and moonlighting developers coding by day in tech parks and hacking together side-gigs in PG rooms at night.
  * 🛺 **Auto & Cab Cartels** (*formerly Syndicate*): Auto union presidents and water tanker operators controlling the local transport stands and collecting protection money.
  * 🥬 **Vendors & Citizens** (*formerly Unaligned*): Kirana shop owners, street-food vendors, and unemployed graduates just trying to survive the traffic and get home.
* **Cutting Chai Microeconomy**: Agents passively lose energy and happiness. To recover, they route to the nearest Dosa stall or Chai Tapri. If they have the cash, they buy a snack (₹15), transferring wealth from their pocket directly to the local business.
* **The Metropolitan Samachar**: The city’s daily tabloid reporting on market saturations, municipal lockdowns, auto union strikes, and local gossip ("Chai Tapri Chatter").

---

## 🧠 Cognitive Sublink Console (Direct Chat with NPCs)

Click on any agent to open their **HUD Operations Dossier** and establish a direct neural sublink to chat with them in real-time.

* **Dynamic Moods**: Their conversational tone shifts dynamically based on their current stats. If an agent is exhausted (`Energy < 30`) or broke, they will snap, complain about local traffic, or yawn mid-sentence.
* **Natural, Unfiltered Human Responses**: We removed robotic AI disclaimers (*"As an AI language model..."*). If you ask something inappropriate, rude, or off-topic, the agent responds like a real local would—with sarcasm, local slang, or a blunt refusal (*"Bhai, dimag mat kharab kar, aage badho!"*).

---

## 🛠️ Quick Start (Windows)

The project is pre-configured for zero setup. 

1. Double-click **`start.bat`** (or run it from your terminal).
2. The script will automatically:
   * Initialize a python virtual environment (`.venv`) and install backend packages.
   * Generate and seed the database with 100 Indian agents and the 20x20 city grid.
   * Install frontend dependencies and launch the dev servers.
   * Open the live React dashboard in your browser.
3. To stop, simply close the command prompt windows.

### Manual Setup (If preferred)

**1. Run the Backend:**
```bash
cd backend
python -m venv .venv
# Activate: Windows -> .venv\Scripts\activate  |  Mac/Linux -> source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed                  # Seeds the database with Indian agent profiles
uvicorn app.main:app --reload       # Runs backend at http://localhost:8000
```

*Run backend tests:*
```bash
cd backend
.venv\Scripts\python -m pytest
```

**2. Run the Frontend:**
```bash
cd frontend
npm install
npm run dev                         # Runs dashboard at http://localhost:5173
```

---

## ⚡ How It Works (Event Sourcing)

Every single action in the city (a transaction at a chai tapri, an extortion shakedown, a new relationship, or a business going bankrupt) is saved as an immutable **Event** in the SQLite database. 

The live world state, the relationship charts, and daily news headlines are all **projections** folded from this event stream. By dragging the **Time Machine** slider, the frontend requests the backend to fold events only up to day *N*, reconstructing the city grid exactly as it was at that millisecond in history.

---

## 🤖 LLM Planning & Vector Memory (Optional)

The simulation runs out-of-the-box using rule-based heuristics. However, if you want agents to behave with complex autonomous agency:

1. **Ollama Integration** (`ollama pull qwen2.5:14b` or `qwen3:8b`): When running, Tier-2 agents will consult the LLM to generate multi-day goals and plans.
2. **ChromaDB**: Enables semantic vector memories for RAG (retrieval-augmented generation) so agents remember past interactions when planning.

The dashboard header badges and `/api/status` endpoint will show you which systems are currently loaded.
