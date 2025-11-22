from fastapi import FastAPI
from pydantic import BaseModel
import os
import requests
from utils import get_ibm_token
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

AGENT_ID = os.getenv("AGENT_ID")
REGION = os.getenv("REGION")

class MessageRequest(BaseModel):
    message: str
    thread_id: str = ""  # optional
    
@app.post("/send")
def send_message(req: MessageRequest):
    try:
        token = get_ibm_token()
        url = f"{os.getenv('WATSON_INSTANCE_URL')}/v1/orchestrate/runs?stream=true"

        payload = {
            "agent_id": AGENT_ID,
            "message": {"role": "user", "content": req.message}
        }
        if req.thread_id:
            payload["thread_id"] = req.thread_id

        headers = {
            "Authorization": f"Bearer {token}",
            "IAM-API_KEY": os.getenv("WATSON_API_KEY"),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers, stream=True)
        response.raise_for_status()

        # Read streamed response line by line
        result = []
        for line in response.iter_lines():
            if line:
                result.append(line.decode('utf-8'))
        
        return {"streamed_response": result}

    except requests.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        return {"error": "Internal Server Error", "detail": str(e)}
        return {"error": "Internal Server Error", "detail": str(e)}
