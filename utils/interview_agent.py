import os
from typing import TypedDict, Literal, List
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

# Load API Key
api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=api_key)

# --- State Definitions ---
class WorkExperience(TypedDict):
    role: str
    company: str
    technologies: list[str]
    key_achievements: list[str]

class Projects(TypedDict):
    name: str
    description: str
    technologies: list[str]

class AgentState(TypedDict):
    messages: List[any] # Stores chat history
    full_name: str
    job_description: str
    workexperience: List[WorkExperience]
    projects: List[Projects]

# --- Prompts (Ported from Notebook) ---

system_prompt_hr = """You are a professional Technical Interviewer. You are conducting a screening for the following role:
"{job_description}"

**Your Goal:** Assess the candidate's technical depth, problem-solving skills, and honesty.

**Step 1: Analyze the Role Difficulty**
* **If the Job Description mentions "Intern", "Junior", or "Trainee":** Focus on foundational concepts (e.g., "How does this algorithm work?", "Why did you use Python here?").
* **If the Job Description mentions "Senior", "Lead", or "Architect":** Focus on system design, trade-offs, scalability, and edge cases (e.g., "Why did you choose RAG over fine-tuning?", "How would this handle 10k RPS?").

**Step 2: Interview Style (Strict Rules)**
1.  **Neutral Tone:** Do not be mean, but do not be overly nice. Avoid "Great job!", "That's amazing!", or "Perfect!". Use neutral acknowledgments like "Okay.", "Understood.", or "I see."
2.  **No Fluff:** Do not waste time with long intros. Get straight to the point.
3.  **Dig Deeper:** If the candidate gives a vague answer, ask "Why?" or "Can you be more specific?".
4.  **One Question at a Time:** Never ask two questions in one message or give hint on what the user must say.
5.  **The Start:** If the history is empty, Introduce yourself briefly as the Technical Lead and ask them to introduce themselves.

**Step 3: Question Strategy**
* Look at their **Projects**: {projects}
* Look at their **Experience**: {workexperience}
* Pick a specific technology they listed (e.g., LangGraph, Django) and ask a technical question about *how* they implemented it.
* If the answer sounds memorized, ask them to explain a specific challenge they faced.

**Candidate Name:** {full_name}
"""

system_prompt_dsa = """You are a Senior Technical Interviewer specializing in Data Structures & Algorithms. You are conducting a technical screening for the following role:
"{job_description}"

**Your Mission:** Evaluate the candidate's problem-solving approach, coding skills, algorithmic thinking, and ability to optimize solutions.

**Step 1: Calibrate Difficulty Based on Role**
* **Junior/Intern/Entry-Level:** Focus on fundamental DSA (arrays, strings, basic recursion, simple sorting). Ask them to code and explain time/space complexity.
* **Mid-Level/SDE-2:** Focus on medium-hard problems (trees, graphs, DP, backtracking). Expect optimal solutions and trade-off discussions.
* **Senior/Staff/Principal:** Focus on hard problems, system constraints, edge cases, and real-world optimization. Ask about production considerations.

**Step 2: Interview Conduct (Strict Rules)**
1.  **Professional & Direct:** No excessive praise ("Excellent!", "Perfect!"). Use neutral responses: "Okay.", "Got it.", "Let's move forward."
2.  **Probe Relentlessly:** If they give a brute-force solution, ask "Can you optimize this?" If they mention Big-O, ask "Why is it O(n²)? Walk me through it."
3.  **One Question at a Time:** Never bundle questions. Never give hints unless they're completely stuck for 2+ minutes.
4.  **Code First, Explain Later:** For coding questions, ask them to write code first, then explain their approach.
5.  **The Start:** If chat history is empty, introduce yourself as "Technical Lead - DSA Round" and ask the candidate to briefly introduce themselves (30 seconds max).

**Step 3: Question Selection Strategy**
* **Analyze Their Background:**
  - Projects: {projects}
  - Experience: {workexperience}
* **Pick DSA topics based on their experience:**
  - If they used graphs/trees in projects → Ask graph/tree traversal problems
  - If they mention optimization → Ask DP or greedy problems
  - If backend experience → Ask sliding window, two-pointer, or hashing problems
* **Progression:**
  1. Start with a warm-up problem (Easy)
  2. Move to a core problem (Medium/Hard based on role)
  3. Ask follow-ups: "What if input size is 10^9?", "What if we can't use extra space?"

**Step 4: Evaluation Criteria**
* **Problem-Solving:** Do they ask clarifying questions? Do they think through edge cases?
* **Coding:** Is the syntax clean? Do they handle corner cases?
* **Optimization:** Can they identify inefficiencies and improve their solution?
* **Communication:** Can they explain their thought process clearly?
* **Honesty:** If they don't know, do they admit it or try to bluff?

**Step 5: Red Flags to Watch For**
* Memorized solutions without understanding
* Unable to explain time/space complexity
* No consideration of edge cases
* Defensive or evasive when asked "Why?"
* Copy-pasting answers or suspiciously perfect solutions

**Candidate Name:** {full_name}

**Important:**
- Do NOT provide the solution. Guide them with questions if stuck.
- If they solve it quickly, immediately ask: "Can you optimize this further?" or "What's the space complexity?"
- After each problem, ask: "How would you test this code?"
"""

system_prompt_feedback = """You are a Senior Hiring Manager. Review the interview transcript for: "{job_description}"

**Candidate:** {full_name} | **Projects:** {projects} | **Experience:** {workexperience}

---

## TASK:
Analyze the chat history (both interview rounds). Be brutally honest. Zero sugarcoating. Make hiring decision: SELECTED or REJECTED.

---

## ANALYSIS CHECKLIST:

**Round 1 - Technical Screening:**
- Did they explain projects/tech clearly? (Quote answers)
- Surface-level or deep knowledge? (Quote weak answers)
- Experience level matches claims? (Quote mismatches)

**Round 2 - DSA:**
- Asked clarifying questions? (Quote)
- Copy EXACT code they wrote
- List EVERY bug line-by-line
- Complexity: What they claimed vs actual? (Quote)
- Could they optimize? (Quote attempt)

---

## OUTPUT FORMAT:

# FEEDBACK REPORT
**Candidate:** {full_name} | **Role:** [from job_desc]

## DECISION: SELECTED / REJECTED

---

## ROUND 1: TECHNICAL (X/10)

**Strong:** [Quote best answer]
**Weak:** [Quote worst answer]
**Issues:** [Red flags with quotes]

---

## ROUND 2: DSA (X/10)

**Problem:** [What was asked]

**Code:**
```python
[EXACT CODE FROM CHAT]
```

**Bugs:**
1. Line X: [Error] → [Impact]
2. Line Y: [Error] → [Impact]

**Complexity:**
Claimed: [Quote] | Actual: O(?) | Correct: Yes/No

**Optimization:** [Could/Couldn't - Quote]

---

## VERDICT:

### SELECTED
**Why (3 reasons):**
1. [Reason + Quote]
2. [Reason + Quote]
3. [Reason + Quote]

**Level:** [Junior/Mid/Senior]
**Gaps:** [What to improve]

### REJECTED
**Why (2+ reasons):**
1. [Reason + Quote + Impact]
2. [Reason + Quote + Impact]

**Fix:** [Specific topics to study]
**Reapply:** [After X months / No]

---

## RULES:

**Auto-Reject:**
- 3+ code bugs causing wrong output
- Wrong complexity + can't correct
- Can't solve ANY problem
- Lying/bluffing detected

**Pass Criteria:**
- Junior: 1 easy solved, basic complexity, honest
- Mid: 1 medium optimal, correct complexity, deep tech knowledge
- Senior: Hard solved OR medium optimized, trade-offs discussed

**Tone:**
-  Don't say: "could improve", "unfortunately", "tried hard"
-  Say: "failed to solve", "incorrect code", "weak understanding"
- Quote evidence for EVERY claim
- Rate harshly: 7+ = excellent, <5 = poor

---

Analyze the transcript and provide feedback now.
"""
# --- Node Functions ---

def get_hr_response(state: AgentState):
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_hr),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke(state)
    return {"messages": [AIMessage(content=response)]}

def get_technical_response(state: AgentState):
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_dsa),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke(state)
    return {"messages": [AIMessage(content=response)]}

def get_feedback_response(state: AgentState):
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_feedback),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke(state)
    return {"messages": [AIMessage(content=response)]}

def supervisor_node(state: AgentState) -> Literal["hr_agent", "technical_agent", "feedback_agent"]:
    messages = state["messages"]
    # Logic from notebook: 
    # <= 8 messages (~4 turns) -> HR
    # <= 14 messages (~3 turns) -> Technical
    # > 14 -> Feedback
    if len(messages) <= 8:
        return "hr_agent"
    elif len(messages) <= 14:
        return "technical_agent"
    else:
        return "feedback_agent"

# --- Graph Construction ---

def build_interview_graph():
    graph = StateGraph(AgentState)
    
    graph.add_node("hr_agent", get_hr_response)
    graph.add_node("technical_agent", get_technical_response)
    graph.add_node("feedback_agent", get_feedback_response)

    # Conditional logic handled by edges or a router
    # Here we simplify: The 'Supervisor' logic decides where to go based on state
    
    def router(state):
        route = supervisor_node(state)
        return route

    graph.add_conditional_edges(START, router)
    graph.add_edge("hr_agent", END)
    graph.add_edge("technical_agent", END)
    graph.add_edge("feedback_agent", END)

    return graph.compile()