from fastapi import FastAPI
from app.api.routes import router
from app.utils.logger import get_logger

log = get_logger("main")

app = FastAPI(
    title="Operational Intelligence Engine",
    description="MVP — mineração de empresas + score operacional (sem DB, sem IA).",
    version="0.1.0",
)
app.include_router(router)


@app.on_event("startup")
async def _startup():
    log.info("OIE iniciado.")
