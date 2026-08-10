from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from livekit import api
import os
import uuid
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOM_NAME = "interview-room"
ACCESS_CODE = os.getenv("ACCESS_CODE", "")

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

@app.get("/get-token")
def get_token(code: str = ""):
    if ACCESS_CODE and code != ACCESS_CODE:
        raise HTTPException(status_code=403, detail="Invalid access code")

    identity = f"candidate-{uuid.uuid4().hex[:8]}"
    token = (
        api.AccessToken()
        .with_identity(identity)
        .with_name("Candidate")
        .with_grants(api.VideoGrants(room_join=True, room=ROOM_NAME))
        .to_jwt()
    )
    return {
        "token": token,
        "url": os.getenv("LIVEKIT_URL"),
        "room": ROOM_NAME,
    }

@app.post("/upload-cv")
async def upload_cv(file: UploadFile):
    contents = await file.read()
    with open("candidate_cv.pdf", "wb") as f:
        f.write(contents)
    return {"status": "uploaded"}

@app.post("/set-role")
async def set_role(job_title: str = Form(...)):
    with open("job_role.txt", "w") as f:
        f.write(job_title.strip())
    return {"status": "saved"}

@app.get("/scorecard")
def get_scorecard():
    if not os.path.exists("scorecard.json"):
        return JSONResponse(status_code=202, content={"status": "not_ready"})
    with open("scorecard.json", "r") as f:
        data = json.load(f)
    return {"status": "ready", "scorecard": data}