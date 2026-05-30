import sys
import asyncio

# Playwright no Windows exige ProactorEventLoop (suporta subprocess).
# Precisa vir ANTES de qualquer import que possa criar um loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.utils.logger import get_logger

log = get_logger("main")

app = FastAPI(
    title="Operational Intelligence Engine",
    description="MVP — mineração de empresas + score operacional (sem DB, sem IA).",
    version="0.1.0",
)

# CORS liberado para o frontend (Vite roda em outra porta/origem em dev).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def _startup():
    log.info("OIE iniciado.")
