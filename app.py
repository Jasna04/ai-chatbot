import os
import csv
import re
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


# =====================================================
# APP SETUP
# =====================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# REQUEST MODEL
# =====================================================

class ChatInput(BaseModel):
    message: str
    site: Optional[str] = "default"


BASE_DIR = os.path.dirname(__file__)
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")


# =====================================================
# SENDGRID CONFIG (SAFE)
# =====================================================

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL")


def send_support_email(subject: str, body: str):
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=SUPPORT_EMAIL,
        subject=subject,
        plain_text_content=body,
    )

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)


def create_support_ticket(site: str, user_message: str):
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"

    email_body = f"""
NEW SUPPORT TICKET

Ticket ID: {ticket_id}
Store: {site.upper()}
Created: {datetime.utcnow().isoformat()} UTC

Customer Message:
{user_message}
"""

    send_support_email(
        subject=f"[{site.upper()}] Support Ticket {ticket_id}",
        body=email_body
    )

    return ticket_id


def detect_escalation_intent(msg: str):
    return any(
        k in msg for k in [
            "talk to human",
            "human support",
            "support agent",
            "customer care",
            "complaint",
            "issue",
            "problem",
            "not happy",
            "help me",
            "escalate"
        ]
    )


# =====================================================
# LOAD ORDERS
# =====================================================

def load_orders(filename):
    path = os.path.join(KNOWLEDGE_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


CHRISTMAS_ORDERS = load_orders("orders.csv")
PARIS_ORDERS = load_orders("paris_orders.csv")

CHRISTMAS_ORDER_IDS = {o["OrderID"].lower() for o in CHRISTMAS_ORDERS if o.get("OrderID")}
PARIS_ORDER_IDS = {o["OrderID"].lower() for o in PARIS_ORDERS if o.get("OrderID")}


def detect_order_id(message: str, valid_ids: set):
    for word in re.findall(r"[A-Za-z0-9\-]+", message.lower()):
        if word in valid_ids:
            return word
    return None


def get_order(order_id: str, orders: list):
    for o in orders:
        if o["OrderID"].lower() == order_id:
            return o
    return None


def detect_order_intent(msg: str):
    if any(k in msg for k in ["delivery", "eta", "delivered"]):
        return "delivery"
    if "status" in msg:
        return "status"
    if any(k in msg for k in ["amount", "total", "price"]):
        return "amount"
    if "item" in msg:
        return "item"
    if "customer" in msg:
        return "customer"
    if "city" in msg or "country" in msg:
        return "location"
    return "full"


# =====================================================
# PARIS PRODUCTS
# =====================================================

def load_paris_products():
    path = os.path.join(KNOWLEDGE_DIR, "womens_collections.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


PARIS_PRODUCTS = load_paris_products()


def find_paris_product(message: str):
    msg = message.lower()
    for p in PARIS_PRODUCTS:
        name = p.get("product_name", "").lower()
        if name and all(k in msg for k in name.split()):
            return p
    return None


def detect_paris_intent(msg: str):
    if "price" in msg:
        return "price"
    if "style" in msg:
        return "style"
    if any(k in msg for k in ["list", "show", "all", "items", "dresses"]):
        return "list"
    return None


# =====================================================
# FRONTEND
# =====================================================

@app.get("/", response_class=HTMLResponse)
def home():
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()


# =====================================================
# CHAT ENDPOINT (AGENTIC)
# =====================================================

@app.post("/chat")
def chat(data: ChatInput):
    msg = data.message.lower().strip()
    site = (data.site or "default").lower()

    # ---------- AGENT DECISION: ESCALATE
    if detect_escalation_intent(msg):
        ticket_id = create_support_ticket(site, data.message)
        return {
            "reply": (
                "🧑‍💼 I've escalated this to our human support team.\n\n"
                f"🎫 Ticket ID: {ticket_id}\n"
                "Our team will contact you shortly."
            )
        }

    # ---------- GREETING
    if msg in ["hi", "hello", "hey"]:
        return {
            "reply": (
                f"👋 Hi! Welcome to the **{site.upper()} store**.\n"
                "You can ask about orders, products, or request human support."
            )
        }

    # ---------- CHRISTMAS STORE
    if site in ["default", "christmas", "india"]:
        order_id = detect_order_id(msg, CHRISTMAS_ORDER_IDS)
        if order_id:
            order = get_order(order_id, CHRISTMAS_ORDERS)
            intent = detect_order_intent(msg)

            if intent == "delivery":
                return {"reply": f"📦 Delivery: {order['DeliveryDate']}"}
            if intent == "status":
                return {"reply": f"📦 Status: {order['OrderStatus']}"}
            if intent == "amount":
                return {"reply": f"📦 Amount: ₹{order['TotalAmount']}"}
            if intent == "item":
                return {"reply": f"📦 Item: {order['ItemName']} (Qty {order['Quantity']})"}

    # ---------- PARIS STORE
    if site == "paris":
        order_id = detect_order_id(msg, PARIS_ORDER_IDS)
        if order_id:
            order = get_order(order_id, PARIS_ORDERS)
            intent = detect_order_intent(msg)

            if intent == "delivery":
                return {"reply": f"📦 Delivery: {order['DeliveryDate']}"}
            if intent == "status":
                return {"reply": f"📦 Status: {order['OrderStatus']}"}
            if intent == "amount":
                return {"reply": f"📦 Amount: €{order['TotalAmountEUR']}"}
            if intent == "item":
                return {"reply": f"📦 Item: {order['ItemName']} (Qty {order['Quantity']})"}
            if intent == "customer":
                return {"reply": f"👤 Customer: {order['CustomerName']}"}
            if intent == "location":
                return {"reply": f"📍 {order['City']}, {order['Country']}"}

        intent = detect_paris_intent(msg)
        product = find_paris_product(msg)

        if product:
            if intent == "price":
                return {"reply": f"👗 {product['product_name']} – €{product['price_eur']}"}
            if intent == "style":
                return {"reply": f"👗 Style: {product['style']}"}

        if intent == "list":
            return {
                "reply": "🇫🇷 Paris Dresses:\n" +
                "\n".join(
                    f"• {p['product_name']} – €{p['price_eur']}"
                    for p in PARIS_PRODUCTS
                )
            }

    return {"reply": "I can help with orders, products, or connect you to human support."}
