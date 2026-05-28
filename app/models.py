from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class CompanyIn(BaseModel):
    empresa: str
    cnpj: Optional[str] = None
    setor: Optional[str] = None
    cidade: Optional[str] = None
    site: Optional[str] = None
    telefone: Optional[str] = None
    linkedin: Optional[str] = None


class Company(CompanyIn):
    id: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AnalyzeRequest(BaseModel):
    company_ids: Optional[list[str]] = None
    collectors: Optional[list[str]] = None


class SubScores(BaseModel):
    dependencia_administrativa: float = 0.0
    processos_repetitivos: float = 0.0
    problemas_atendimento: float = 0.0
    crescimento: float = 0.0
    complexidade_operacional: float = 0.0
    maturidade_digital_baixa: float = 0.0


class ScoreOut(BaseModel):
    company_id: str
    empresa: str
    score: float
    confidence: float
    subscores: SubScores
    signals: list[str]
    observacoes: str
    trigger_event: Optional[str] = None
    playbook: Optional[str] = None


class CommercialFeedback(BaseModel):
    company_id: str
    resultado: str  # ex.: reuniao_marcada | sem_resposta | desqualificado | em_negociacao
    nota: Optional[str] = None
