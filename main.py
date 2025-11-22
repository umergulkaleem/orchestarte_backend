from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, json, requests
from utils import get_ibm_token
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENT_ID = os.getenv("AGENT_ID")
REGION = os.getenv("REGION")

class MessageRequest(BaseModel):
    message: str
    thread_id: str = ""  # optional

@app.post("/send")
def send_message(req: MessageRequest):
    print("Received message:", req.message)
    try:
        token = get_ibm_token()
        print("Got IBM token:", token[:10], "...")

        url = f"{os.getenv('WATSON_INSTANCE_URL')}/v1/orchestrate/runs?stream=true"
        print("Calling URL:", url)

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

        assistant_text = ""
        streamed_response = []

        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                streamed_response.append(decoded)
                try:
                    data = json.loads(decoded)
                    if data.get("event") == "message.created":
                        # extract text from Watson Orchestrate response
                        contents = data["data"]["message"]["content"]
                        for c in contents:
                            if c.get("response_type") == "text":
                                assistant_text += c.get("text", "")
                except Exception as e:
                    print("JSON parse error:", e)
                    continue

        print("Assistant text:", assistant_text)
        return {"streamed_response": streamed_response, "assistant_text": assistant_text}

    except requests.HTTPError as e:
        print("HTTP error:", e.response.status_code, e.response.text)
        return {"error": f"HTTP error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        print("Exception occurred:", str(e))
        return {"error": "Internal Server Error", "detail": str(e)}
