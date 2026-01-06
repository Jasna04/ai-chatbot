import os
import csv
import re

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
# Utility: extract order_id
# -------------------------
def extract_order_id(text: str):
    match = re.search(r"\b\d+\b", text)
    return match.group(0) if match else None


# -------------------------
# Load & filter orders.csv
# -------------------------
def load_orders_knowledge(order_id: str | None) -> str:
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "knowledge", "orders.csv")

    if not os.path.exists(file_path):
        return ""

    matched_rows = []

    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            if order_id:
                # Match order_id column (case-insensitive)
                for key, value in row.items():
                    if "order" in key.lower() and str(value) == order_id:
                        matched_rows.append(row)
            else:
                matched_rows.append(row)

    if not matched_rows:
        return ""

    # Convert rows to readable text
    knowledge = []
    for row in matched_rows:
        row_text = ", ".join(
            f"{k}: {v}" for k, v in row.items() if v
        )
        knowledge.append(row_text)

    return "\n".join(knowledge)


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
    user_message = data.message.strip().lower()

    # ✅ Handle greetings first
    if user_message in ["hi", "hello", "hey", "good morning", "good evening"]:
        return {
            "reply": (
                "👋 Hi! I can help you with order details.\n\n"
                "Try asking:\n"
                "- What is the status of order 123?\n"
                "- When will order 456 be delivered?"
            )
        }

    order_id = extract_order_id(user_message)
    knowledge = load_orders_knowledge(order_id)

    if not knowledge:
        return {
            "reply": "I don’t have information for that order."
        }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"""
You are an order support assistant.

The data below contains order records.
Each line represents ONE order.

Answer clearly and concisely using ONLY this data.

DATA:
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
