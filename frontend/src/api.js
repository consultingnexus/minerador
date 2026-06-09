// Cliente da API de prospecção.
//
// Por padrão chama o backend direto em http://localhost:8000 (CORS liberado).
// Dá pra sobrescrever criando um .env.local com:
//   VITE_API_BASE=http://localhost:8000
// ou, se preferir usar o proxy do Vite, VITE_API_BASE=/api

const API_BASE = import.meta.env.VITE_API_BASE

export async function searchProspects({ setor, regiao, maxResultados }) {
  const params = new URLSearchParams({
    setor,
    regiao,
    max_resultados: String(maxResultados),
  });

  // Enviando o header necessário para o Localtunnel pular a tela de aviso automaticamente
  const resp = await fetch(`${API_BASE}/prospect/search?${params.toString()}`, {
    method: "GET",
    headers: {
      "bypass-tunnel-reminder": "true"
    }
  });

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (body && body.detail) detail = body.detail;
    } catch {
      // resposta sem JSON — mantém o detalhe genérico
    }
    throw new Error(detail);
  }

  return resp.json();
}