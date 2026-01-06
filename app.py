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
    fi
