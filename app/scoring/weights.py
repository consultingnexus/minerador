"""Pesos do score composto. Soma não precisa ser 100 — é apenas ponderação."""

WEIGHTS = {
    "dependencia_administrativa": 20,
    "processos_repetitivos": 12,
    "problemas_atendimento": 22,
    "crescimento": 14,
    "complexidade_operacional": 18,
    "maturidade_digital_baixa": 14,
}

# Palavras-chave para sinais de atendimento ruim (reviews/notícias)
NEG_REVIEW_KEYWORDS = [
    "demora", "demorou", "atraso", "atrasou", "atendimento ruim", "pessimo", "péssimo",
    "horrivel", "horrível", "desorganiza", "desorganização", "descaso",
    "nao respond", "não respond", "ninguem atende", "ninguém atende",
    "burocra", "fila", "espera", "lentidao", "lentidão",
]

# Negações que devem invalidar o hit ("não houve demora")
NEGATIONS = ["não", "nao", "sem", "nunca", "jamais", "nenhum", "nenhuma"]

REPETITIVE_AREAS = {"administrativo", "operacional"}

# Decay: meia-vida em dias para sinais com timestamp
HALF_LIFE_DAYS = 180
