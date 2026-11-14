# OmniRoute AI — Hackathon & Recruitment Demo Script

Follow this step-by-step walkthrough to present the platform to evaluators in 5 to 7 minutes.

---

## Step 1: Open the Operations Dashboard
- **Action:** Open browser at `http://localhost:8000`.
- **Narration:**
  > "Welcome to OmniRoute AI. Here on the Operations Dashboard, you see live telemetry across 1,000+ customer tickets and 100 human support agents. Notice our current SLA compliance is 95.4%, with live tracking of running, at-risk, and breached tickets."

---

## Step 2: Live Omnichannel Complaint Ingestion
- **Action:** Click **Omnichannel Tester (Email/Chat/Phone)** in the sidebar.
- **Input Demo Query:**
  - Channel: `Email`
  - Customer: `CUS-000001`
  - Subject: `No internet on my JioFiber broadband`
  - Body: `My router has shown red light and no internet for 2 days. This is the third time this month.`
- **Action:** Click **Submit Ticket**.
- **Narration:**
  > "Watch what happens in under 20 milliseconds:
  > 1. Our hybrid NLP engine classifies the intent as `TECHNICAL_ISSUE` requiring the `INFRA_SYSADMIN` skill.
  > 2. It detects the 2-day duration and recurrence, flagging High Customer Impact.
  > 3. The independent SLA engine starts two separate clocks: a First Response clock and a Resolution clock.
  > 4. The routing engine filters all 100 agents, scores eligible candidates using our normalized formula $0.35S + 0.25L + 0.25C + 0.15E$, and assigns an on-shift network specialist with free capacity."

---

## Step 3: Inspect the Routing Decision & Explainability
- **Action:** Navigate to **Routing Decision Explorer**.
- **Narration:**
  > "Enterprise evaluators care about explainability. Notice how OmniRoute displays why the selected agent was chosen, the exact score breakdown across skill, language, capacity, and experience, as well as every rejected agent and their specific rejection reason—such as off-shift, wrong skill, or at capacity limit."

---

## Step 4: Demonstrate Dual SLA Clocks & Pause/Resume
- **Action:** Navigate to **SLA Monitoring**.
- **Action:** Click on the newly created ticket.
- **Narration:**
  > "Our SLA engine runs two independent clocks. Automated bot acknowledgments do NOT stop the First Response clock—only a qualifying human response counts. Furthermore, when an agent places a ticket on hold waiting for the customer, the SLA clock pauses and the deadline is automatically extended by the paused duration."

---

## Step 5: Explore the 100-Agent Capacity Roster
- **Action:** Click **Agent Capacity Roster**.
- **Narration:**
  > "Here are our 100 simulated human agents, generated deterministically with Faker using fixed seed `20261022`. Every agent has verified skill proficiencies, supported languages, working shifts, and real-time concurrency load bars. Our atomic SQL reservation ensures that simultaneous incoming tickets never exceed an agent's maximum capacity."

---

## Step 6: The Grand Finale — 3-Way Simulation Lab
- **Action:** Navigate to **Evaluation Lab**.
- **Action:** Click **Run 500-Ticket Comparative Benchmark**.
- **Narration:**
  > "To prove the mathematical superiority of OmniRoute AI, our Simulation Lab compares Round-Robin, Skill-Based Routing, and OmniRoute on 500 real database tickets under identical initial conditions.
  > - Round-Robin fails on skills (only 68.8% match).
  > - Skill-Based routing causes catastrophic capacity violations (98.6% overcapacity).
  > - OmniRoute achieves 99.8% skill match, 100% language match, **0.0% capacity violations**, and reduces average customer wait time by 77.4%."
