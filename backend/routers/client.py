
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

@router.get("/client/dashboard", response_class=HTMLResponse)
def client_dashboard(request: Request):
    return templates.TemplateResponse("client/dashboard.html", {"request": request})
