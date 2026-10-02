from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import hashlib
import secrets
from datetime import datetime
from dotenv import load_dotenv

from gemini_utils import get_recommendation

load_dotenv()

app = FastAPI(
    title="PocketSmart AI",
    description="Your Smart Budget & Recommendation Assistant",
    version="1.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DATABASE = "pocketsmart.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            budget REAL NOT NULL,
            input_data TEXT,
            recommendation TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        100000
    )

    return f"{salt}${password_hash.hex()}"


def verify_password(password: str, stored_password: str) -> bool:
    try:
        salt, stored_hash = stored_password.split("$")

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100000
        )

        return secrets.compare_digest(
            password_hash.hex(),
            stored_hash
        )

    except Exception:
        return False


def get_current_user(request: Request):
    user_id = request.cookies.get("user_id")

    if not user_id:
        return None

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    conn.close()

    return user


def require_login(request: Request):
    return get_current_user(request)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    user = get_current_user(request)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "user": user
        }
    )


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "request": request,
            "error": None
        }
    )


@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):

    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password:

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "request": request,
                "error": "All fields are required."
            }
        )

    if len(password) < 6:

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "request": request,
                "error": "Password must contain at least 6 characters."
            }
        )

    conn = get_db()

    existing_user = conn.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if existing_user:

        conn.close()

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "request": request,
                "error": "An account with this email already exists."
            }
        )

    password_hash = hash_password(password)

    conn.execute(
        """
        INSERT INTO users
        (username, email, password, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            username,
            email,
            password_hash,
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()

    return RedirectResponse(
        "/login",
        status_code=303
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,
            "error": None
        }
    )


@app.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):

    email = email.strip().lower()

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    conn.close()

    if not user or not verify_password(
        password,
        user["password"]
    ):

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "request": request,
                "error": "Invalid email or password."
            }
        )

    response = RedirectResponse(
        "/dashboard",
        status_code=303
    )

    response.set_cookie(
        key="user_id",
        value=str(user["id"]),
        httponly=True,
        samesite="lax"
    )

    response.set_cookie(
        key="username",
        value=user["username"],
        httponly=True,
        samesite="lax"
    )

    return response


@app.get("/logout")
async def logout():

    response = RedirectResponse(
        "/",
        status_code=303
    )

    response.delete_cookie("user_id")
    response.delete_cookie("username")

    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):

    user = require_login(request)

    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )

    conn = get_db()

    recommendations = conn.execute(
        """
        SELECT *
        FROM recommendations
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 5
        """,
        (user["id"],)
    ).fetchall()

    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "user": user,
            "recommendations": recommendations
        }
    )


@app.get("/home-planner", response_class=HTMLResponse)
async def home_planner(request: Request):

    user = require_login(request)

    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="home_planner.html",
        context={
            "request": request,
            "user": user
        }
    )


@app.post("/generate-home")
async def generate_home(
    request: Request,
    budget: float = Form(...),
    room: str = Form(...),
    style: str = Form(...),
    requirements: str = Form("")
):

    user = require_login(request)

    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )

    input_data = (
        f"Room: {room}\n"
        f"Style: {style}\n"
        f"Requirements: {requirements}"
    )

    recommendation = get_recommendation(
        category="Home Interior",
        budget=budget,
        details=input_data
    )

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO recommendations
        (user_id, category, budget, input_data, recommendation, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            "Home Interior",
            budget,
            input_data,
            recommendation,
            datetime.now().isoformat()
        )
    )

    conn.commit()

    recommendation_id = cursor.lastrowid

    conn.close()

    return RedirectResponse(
        f"/recommendations-details/{recommendation_id}",
        status_code=303
    )


@app.get("/party-planner", response_class=HTMLResponse)
async def party_planner(request: Request):

    user = require_login(request)

    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="party_planner.html",
        context={
            "request": request,
            "user": user
        }
    )


@app.post("/generate-party")
async def generate_party(
    request: Request,
    budget: float = Form(...),
    event_type: str = Form(...),
    guests: int = Form(...),
    location: str = Form(...),
    requirements: str = Form("")
):

    user = require_login(request)

    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )

    input_data = (
        f"Event Type: {event_type}\n"
        f"Guests: {guests}\n"
        f"Location: {location}\n"
        f"Requirements: {requirements}"
    )

    recommendation = get_recommendation(
        category="Party Planning",
        budget=budget,
        details=input_data
    )

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO recommendations
        (user_id, category, budget, input_data, recommendation, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            "Party Planning",
            budget,
            input_data,
            recommendation,
            datetime.now().isoformat()
        )
    )

    conn.commit()

    recommendation_id = cursor.lastrowid

    conn.close()

    return RedirectResponse(
        f"/recommendations-details/{recommendation_id}",
        status_code=303
    )


@app.get("/jewelry-planner", response_class=HTMLResponse)
async def jewelry_planner(request: Request):

    user = require_login(request)

    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="jewelry_planner.html",
        context={
            "request": request,
            "user": user
        }
    )


@app.post("/generate-jewelry")
async def generate_jewelry(
    request: Request,
    budget: float = Form(...),
    occasion: str = Form(...),
    jewelry_type: str = Form(...),
    preferred_color: str = Form(...),
    requirements: str = Form(""),
    outfit_image: UploadFile = File(None)
):

    user = require_login(request)

    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )

    image_name = ""

    if outfit_image and outfit_image.filename:
        image_name = outfit_image.filename

    input_data = (
        f"Occasion: {occasion}\n"
        f"Jewelry Type: {jewelry_type}\n"
        f"Preferred Color: {preferred_color}\n"
        f"Requirements: {requirements}\n"
        f"Outfit Image: "
        f"{image_name if image_name else 'Not uploaded'}"
    )

    recommendation = get_recommendation(
        category="Jewelry",
        budget=budget,
        details=input_data
    )

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO recommendations
        (user_id, category, budget, input_data, recommendation, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            "Jewelry",
            budget,
            input_data,
            recommendation,
            datetime.now().isoformat()
        )
    )

    conn.commit()

    recommendation_id = cursor.lastrowid

    conn.close()

    return RedirectResponse(
        f"/recommendations-details/{recommendation_id}",
        status_code=303
    )


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):

    user = require_login(request)

    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )

    conn = get_db()

    recommendations = conn.execute(
        """
        SELECT *
        FROM recommendations
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user["id"],)
    ).fetchall()

    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "request": request,
            "user": user,
            "recommendations": recommendations
        }
    )


@app.get(
    "/recommendations-details/{recommendation_id}",
    response_class=HTMLResponse
)
async def recommendation_details(
    request: Request,
    recommendation_id: int
):

    user = require_login(request)

    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )

    conn = get_db()

    recommendation = conn.execute(
        """
        SELECT *
        FROM recommendations
        WHERE id = ? AND user_id = ?
        """,
        (
            recommendation_id,
            user["id"]
        )
    ).fetchone()

    conn.close()

    if not recommendation:
        return HTMLResponse(
            "Recommendation not found.",
            status_code=404
        )

    return templates.TemplateResponse(
        request=request,
        name="recommendation_detail.html",
        context={
            "request": request,
            "user": user,
            "recommendation": recommendation
        }
    )


@app.get("/session-info")
async def session_info(request: Request):

    user = get_current_user(request)

    if not user:
        return {
            "logged_in": False
        }

    return {
        "logged_in": True,
        "user_id": user["id"],
        "username": user["username"],
        "email": user["email"]
    }


@app.get("/session-data")
async def session_data(request: Request):

    user = get_current_user(request)

    if not user:
        return {
            "logged_in": False,
            "data": None
        }

    conn = get_db()

    recommendations = conn.execute(
        """
        SELECT id, category, budget, created_at
        FROM recommendations
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user["id"],)
    ).fetchall()

    conn.close()

    return {
        "logged_in": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        },
        "recommendations": [
            dict(row) for row in recommendations
        ]
    }


@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "application": "PocketSmart AI"
    }


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )