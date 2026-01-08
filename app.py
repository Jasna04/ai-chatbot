import os
import csv
import re
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


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
# CHRISTMAS STORE – ORDERS (INR)
# =====================================================

def load_orders(filename):
    path = os.path.join(KNOWLEDGE_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


CHRISTMAS_ORDERS = load_orders("orders.csv")
CHRISTMAS_ORDER_IDS = {
    o["OrderID"].lower() for o in CHRISTMAS_ORDERS if o.get("OrderID")
}


# =====================================================
# PARIS STORE – ORDERS (EUR)
# =====================================================

PARIS_ORDERS = load_orders("paris_orders.csv")
PARIS_ORDER_IDS = {
    o["OrderID"].lower() for o in PARIS_ORDERS if o.get("OrderID")
}


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
    if "customer" in msg or "name" in msg:
        return "customer"
    if "city" in msg or "country" in msg:
        return "location"
    return "full"


# =====================================================
# CHRISTMAS STORE – PRODUCTS (INR)
# =====================================================

def load_products():
    path = os.path.join(KNOWLEDGE_DIR, "products.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


PRODUCTS = load_products()
PRODUCT_IDS = {p["Product ID"].lower() for p in PRODUCTS if p.get("Product ID")}


def detect_product_id(message: str):
    for word in re.findall(r"[A-Za-z0-9\-]+", message.lower()):
        if word in PRODUCT_IDS:
            return word
    return None


def get_product(pid: str):
    for p in PRODUCTS:
        if p["Product ID"].lower() == pid:
            return p
    return None


def detect_product_intent(msg: str):
    if "price" in msg:
        return "price"
    if "available" in msg or "stock" in msg:
        return "availability"
    if "description" in msg or "about" in msg:
        return "description"
    return None


# =====================================================
# PARIS STORE – PRODUCTS (EUR)
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
        if not name:
            continue
        if all(k in msg for k in name.split()):
            return p
    return None


def detect_paris_intent(msg: str):
    if any(k in msg for k in ["price", "cost"]):
        return "price"
    if "style" in msg or "type" in msg:
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
# CHAT ENDPOINT
# =====================================================

@app.post("/chat")
def chat(data: ChatInput):
    msg = data.message.lower().strip()
    site = (data.site or "default").lower()

    # ---------- Greeting
    if msg in ["hi", "hello", "hey"]:
        return {
            "reply": (
                f"👋 Hi! Welcome to the **{site.upper()} store**.\n\n"
                "Try:\n"
                "- Status of order PR1001\n"
                "- Delivery of order PR1002\n"
                "- Price of Cocktail Dress\n"
                "- Show western dresses"
            )
        }

    # =================================================
    # CHRISTMAS STORE
    # =================================================
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

    # =================================================
    # PARIS STORE – ORDERS (EUR)
    # =================================================
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

            return {
                "reply": (
                    f"📦 Order {order['OrderID']}\n"
                    f"Customer: {order['CustomerName']}\n"
                    f"Item: {order['ItemName']}\n"
                    f"Amount: €{order['TotalAmountEUR']}\n"
                    f"Status: {order['OrderStatus']}"
                )
            }

        # ---------- Paris products (existing logic)
        intent = detect_paris_intent(msg)
        product = find_paris_product(msg)

        if product:
            if intent == "price":
                return {"reply": f"👗 {product['product_name']} – €{product['price_eur']}"}
            if intent == "style":
                return {"reply": f"👗 Style: {product['style']}"}

        if intent == "list":
            return {
                "reply": "🇫🇷 Paris Western Dresses:\n" +
                "\n".join(
                    f"• {p['product_name']} – €{p['price_eur']}"
                    for p in PARIS_PRODUCTS
                )
            }

    return {"reply": "Please ask about products or orders."}
