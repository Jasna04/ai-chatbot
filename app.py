import os
import csv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI

# -------------------------
# App setup
# -------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI()

# -------------------------
# Request model
# -------------------------
class ChatInput(BaseModel):
    message: str


# -------------------------
# Load knowledge from orders.csv
# -------------------------
def load_orders_knowledge() -> str:
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Knowledge", "orders.csv")

    knowledge = []

    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            knowledge.append(
                f"Q: {row['question']}\nA: {row['answer']}"
            )

    return "\n\n".join(knowledge)


# -------------------------
# Serve frontend UI
# -------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# -------------------------
# Chat endpoint
# -------------------------
@app.post("/chat")
def chat(data: ChatInput):
    knowledge = load_orders_knowledge()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"""
You are an order support chatbot.
Answer ONLY using the knowledge below.
If the answer is not present, say:
"I don't have that information yet."

KNOWLEDGE:
{knowledge}
"""
            },
            {
                "role": "user",
                "content": data.message
            }
        ]
    )

    return {"reply": response.choices[0].message.content}
