from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/game/ideal", response_class=HTMLResponse)
def menu_worldcup(request: Request):
    return templates.TemplateResponse("game_worldcup.html", {"request": request})
