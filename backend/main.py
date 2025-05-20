from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi import status
import sqlite3
import secrets

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(16))
app.mount("/static", StaticFiles(directory="backend/static"), name="static")
templates = Jinja2Templates(directory="backend/templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DB = "backend/users.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.on_event("startup")
def startup():
    conn = get_db()

    # Create users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN NOT NULL DEFAULT 0
        )
    """)

    # Create logs table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register")
def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register_post(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_db()
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    hashed_password = pwd_context.hash(password)

    try:
        # Only the first user gets admin privileges
        is_admin = 1 if user_count == 0 else 0
        conn.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
            (username, hashed_password, is_admin)
        )
        conn.commit()
        return RedirectResponse("/login", status_code=303)
    except sqlite3.IntegrityError:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username already exists"
        })
    finally:
        conn.close()




@app.get("/login")
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user and pwd_context.verify(password, user["password"]):
        request.session["user"] = dict(user)
        conn.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", (user["id"], "login"))
        conn.commit()
        return RedirectResponse("/client/dashboard", status_code=303)
    
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@app.get("/client/dashboard")
def client_dashboard(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("client/dashboard.html", {"request": request, "user": user})

@app.get("/admin/dashboard")
def admin_dashboard(request: Request, user: dict = Depends(get_current_user)):
    if not user.get("is_admin"):
        # User is logged in but NOT admin, forbid access
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access only")
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "user": user, "show_admin_controls": True})

@app.get("/admin/users")
def list_users(request: Request, user: dict = Depends(get_current_user)):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admins only")
    conn = get_db()
    users = conn.execute("SELECT id, username, is_admin FROM users").fetchall()
    conn.close()
    return templates.TemplateResponse("admin/users.html", {"request": request, "users": users, "user": user, "show_admin_controls": True})

@app.post("/admin/toggle-role")
def toggle_user_role(request: Request, user_id: int = Form(...), current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403)
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        new_role = 0 if user["is_admin"] else 1
        conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.post("/admin/delete-user")
def delete_user(request: Request, user_id: int = Form(...), current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403)

    # Prevent admin from deleting themselves
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself.")

    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    return RedirectResponse("/admin/users", status_code=303)

@app.get("/admin/logs")
def view_logs(request: Request, user: dict = Depends(get_current_user)):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    conn = get_db()
    logs = conn.execute("""
        SELECT logs.id, users.username, logs.action, logs.timestamp
        FROM logs
        JOIN users ON logs.user_id = users.id
        ORDER BY logs.timestamp DESC
    """).fetchall()
    conn.close()

    return templates.TemplateResponse("admin/logs.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "show_admin_controls": True
    })


#from fastapi import FastAPI
#from fastapi.staticfiles import StaticFiles
#from starlette.middleware.sessions import SessionMiddleware
#from .routers import public, client, admin
#from .database import Base, engine
#import os

#Base.metadata.create_all(bind=engine)

#app = FastAPI()
#app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "mysecret"))
#app.mount("/static", StaticFiles(directory="static"), name="static")

#app.include_router(public.router)
#app.include_router(client.router)
#app.include_router(admin.router)
##