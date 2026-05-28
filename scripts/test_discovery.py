"""Teste isolado do coletor maps_discovery, sem subir uvicorn."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.collectors.maps_discovery import collect_maps_discovery


async def main():
    print("Iniciando teste de descoberta...")
    rows = await collect_maps_discovery("clinicas", "Itapevi", max_resultados=3)
    print(f"\n>>> total coletado: {len(rows)}")
    for i, r in enumerate(rows, 1):
        print(f"\n[{i}] {r['empresa']}")
        print(f"    endereço: {r['endereco']}")
        print(f"    telefone: {r['telefone']}")
        print(f"    website:  {r['website'] or '(sem site)'}")
        print(f"    maps url: {r['url_maps'][:80]}...")


if __name__ == "__main__":
    asyncio.run(main())
