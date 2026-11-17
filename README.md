\# AI Voice Interviewer



A real-time voice interview agent. You enter the job role and optionally upload your CV, then have a spoken interview with an AI interviewer. It asks role-specific questions, follows up on vague answers, references projects from your CV, and decides for itself when the interview is complete. Afterwards, it scores you from 1–5 on four skills and writes a short summary.



Built during my AI Engineering internship at e\& (Etisalat), June–August 2026.



| During the interview | Results |

|---|---|

| !\[Interview](screenshots/interview.png) | !\[Scorecard](screenshots/scorecard.png) |



\## Features



\- \*\*Real-time voice conversation:\*\* low-latency speech in both directions over WebRTC

\- \*\*Role-aware questions:\*\* tailored to the job title you enter, or the agent asks what role you want

\- \*\*CV personalisation:\*\* an uploaded PDF CV is parsed and used to ask about your actual projects and experience

\- \*\*Natural interview flow:\*\* asks follow-ups, chooses when enough has been covered (usually 5–8 exchanges), then ends the call politely by itself

\- \*\*Automatic scorecard:\*\* after the call, the full transcript is evaluated on Technical Skills, Communication, Problem Solving and Confidence, with a written summary

\- \*\*Optional access code:\*\* restricts who can start an interview



\## Architecture



```

Browser (index.html)

&#x20;  │  1. Upload CV / set role ─────────────► FastAPI backend (main.py)

&#x20;  │  2. Request access token ◄────────────      │

&#x20;  │                                              │ saves CV + role to disk

&#x20;  │  3. Join room (WebRTC audio)                 │

&#x20;  ▼                                              ▼

LiveKit room ◄──────────────────────► Voice agent (agent.py)

&#x20;                                        │

&#x20;                                        ├─ Silero VAD    – detects when you start/stop speaking

&#x20;                                        ├─ Deepgram Nova-3 – speech-to-text

&#x20;                                        ├─ GPT-OSS 120B via Groq – interviewer reasoning

&#x20;                                        └─ Cartesia      – text-to-speech

&#x20;                                        │

&#x20;                                        ▼ on call end

&#x20;                                   Transcript → LLM evaluation → scorecard.json

&#x20;  ▲                                              │

&#x20;  └── 4. Poll /scorecard ◄───────────────────────┘

```



\## Tech Stack



| Component | Technology |

|---|---|

| Real-time audio | LiveKit Agents (WebRTC) |

| Speech-to-text | Deepgram Nova-3 |

| LLM | GPT-OSS 120B via Groq (originally Llama 3.3 70B, migrated after Groq retired it) |

| Text-to-speech | Cartesia |

| Voice activity detection | Silero VAD |

| Backend | FastAPI |

| CV parsing | pypdf |

| Frontend | HTML/JS with the LiveKit client SDK |



\## API (backend)



| Method | Endpoint | Purpose |

|---|---|---|

| GET | `/` | Serves the web interface |

| POST | `/upload-cv` | Uploads the candidate's CV (PDF) |

| POST | `/set-role` | Saves the target job title |

| GET | `/get-token?code=` | Returns a LiveKit access token to join the interview room |

| GET | `/scorecard` | Returns the scorecard (`202` while it's still being generated) |



\## Running Locally



1\. Clone the repo and install dependencies (Python 3.11):

&#x20;  ```

&#x20;  git clone https://github.com/uzair852/voice-interviewer.git

&#x20;  cd voice-interviewer

&#x20;  pip install -r requirements.txt

&#x20;  python agent.py download-files

&#x20;  ```

2\. Create a `.env` file:

&#x20;  ```

&#x20;  LIVEKIT\_URL=wss://your-project.livekit.cloud

&#x20;  LIVEKIT\_API\_KEY=your\_livekit\_key

&#x20;  LIVEKIT\_API\_SECRET=your\_livekit\_secret

&#x20;  DEEPGRAM\_API\_KEY=your\_deepgram\_key

&#x20;  CARTESIA\_API\_KEY=your\_cartesia\_key

&#x20;  GROQ\_API\_KEY=your\_groq\_key

&#x20;  ACCESS\_CODE=optional\_code

&#x20;  ```

&#x20;  A free LiveKit Cloud project is enough.

3\. Start the backend and the agent in two terminals:

&#x20;  ```

&#x20;  uvicorn main:app --reload

&#x20;  ```

&#x20;  ```

&#x20;  python agent.py dev

&#x20;  ```

4\. Open http://localhost:8000, enter a role, optionally upload a CV, and start the interview.



\## Known Limitations



\- \*\*One interview at a time:\*\* all candidates join the same room, and the CV, role and scorecard are stored as single files.

\- \*\*Shared disk required:\*\* the backend and agent exchange the CV, role and scorecard through local files, so they need to run on the same machine. Deploying them as separate containers (`Dockerfile.backend` and `Dockerfile.agent`) would need shared storage or a database instead.



Next steps would be per-session rooms and storing session data in a database, so multiple candidates can be interviewed at the same time.

