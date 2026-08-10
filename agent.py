import json
from livekit.agents.beta.tools import EndCallTool
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent
from livekit.plugins import deepgram, cartesia, groq, silero
from pypdf import PdfReader
from groq import Groq
import os

load_dotenv()

groq_client = Groq()

BASE_INSTRUCTIONS = """
You are a professional AI job interviewer conducting a voice interview.

Your job:
1. Ask one question at a time. Ask natural follow-up questions when an answer is
   vague, surprising, or worth digging into further, just like a real interviewer would.
2. Use your own judgment on when you've covered enough ground (typically 5-8 exchanges)
   rather than sticking to a fixed number of questions.
3. When you feel the interview is complete, thank the candidate, briefly mention next
   steps ("we'll be in touch"), and end the conversation politely.

Keep every response short and conversational, since this is a spoken conversation, not text.
"""

def get_job_role():
    role_path = "job_role.txt"
    if not os.path.exists(role_path):
        return None
    with open(role_path, "r") as f:
        role = f.read().strip()
    return role if role else None

def get_cv_text():
    cv_path = "candidate_cv.pdf"
    if not os.path.exists(cv_path):
        return None
    reader = PdfReader(cv_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

def build_instructions():
    job_role = get_job_role()
    cv_text = get_cv_text()

    instructions = BASE_INSTRUCTIONS

    if job_role:
        instructions += f"""

The candidate is interviewing for this specific role: "{job_role}".
Base your questions on what this role typically requires — technical skills, soft
skills, relevant experience, and situational/behavioral questions. Do NOT ask the
candidate what role they want; you already know it. Start the conversation by
briefly confirming the role and diving into your first question.
"""
    else:
        instructions += """

No specific role was provided in advance. Start by greeting the candidate and asking
what role they'd like to be interviewed for today, then proceed based on their answer.
"""

    if cv_text:
        instructions += f"""

The candidate has also submitted the following CV. Use it to personalize your
questions where relevant — ask about specific projects, roles, or skills mentioned
in it, in the context of the target role above:

--- CANDIDATE CV START ---
{cv_text}
--- CANDIDATE CV END ---
"""

    return instructions

def generate_scorecard(transcript_text: str):
    prompt = f"""
You are evaluating a job interview transcript. Based on the conversation below,
rate the candidate from 1-5 (5 being excellent) in each of these domains:
- Technical Skills
- Communication
- Problem Solving
- Confidence

Also write a 2-3 sentence overall summary of the candidate's performance.

Respond with ONLY valid JSON, no other text, in exactly this format:
{{
  "technical_skills": <1-5>,
  "communication": <1-5>,
  "problem_solving": <1-5>,
  "confidence": <1-5>,
  "summary": "<2-3 sentence summary>"
}}

TRANSCRIPT:
{transcript_text}
"""
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Could not parse scorecard", "raw": raw}

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    if os.path.exists("scorecard.json"):
        os.remove("scorecard.json")

    job_role = get_job_role()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=cartesia.TTS(),
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=Agent(
            instructions=build_instructions(),
            tools=[
                EndCallTool(
                    delete_room=True,
                    extra_description="Call this only after you have thanked the candidate and mentioned next steps.",
                    end_instructions="Say a brief, warm goodbye to the candidate.",
                )
            ],
        ),
    )

    if job_role:
        greeting = f"Greet the candidate briefly, confirm they're interviewing for the {job_role} role, and ask your first question."
    else:
        greeting = "Greet the candidate briefly and ask what role they'd like to be interviewed for today."

    await session.generate_reply(instructions=greeting)

    async def on_session_close():
        transcript_text = ""
        for item in session.history.items:
            if item.type == "message" and item.role in ("user", "assistant"):
                content = item.text_content or ""
                transcript_text += f"{item.role.upper()}: {content}\n"

        if transcript_text.strip():
            scorecard = generate_scorecard(transcript_text)
            print("\n===== INTERVIEW SCORECARD =====")
            print(json.dumps(scorecard, indent=2))
            print("================================\n")

            with open("scorecard.json", "w") as f:
                json.dump(scorecard, f, indent=2)

    ctx.add_shutdown_callback(on_session_close)

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))