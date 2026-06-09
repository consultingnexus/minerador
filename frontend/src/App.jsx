import { useState, useEffect } from "react";
import { searchProspects } from "./api.js";
import { toWhatsappLink } from "./whatsapp.js";

const SETORES = [
  "clínicas", "pet shops", "oficinas mecânicas", "restaurantes", 
  "academias", "salões de beleza", "dentistas", "escritórios de advocacia", 
  "imobiliárias", "contabilidade"
];

const REGIOES = [
  "Itapevi", "Barueri", "Osasco", "Carapicuíba", 
  "Jandira", "Cotia", "São Paulo", "Santana de Parnaíba"
];

export default function App() {
  const [setor, setSetor] = useState("clínicas");
  const [regiao, setRegiao] = useState("Itapevi");
  const [maxResultados, setMaxResultados] = useState(30);
  const [filtroSite, setFiltroSite] = useState("todos");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // 1. Inicializa o estado 'data' tentando carregar o histórico salvo no localStorage
  const [data, setData] = useState(() => {
    const salvo = localStorage.getItem("prospeccao_data");
    return salvo ? JSON.parse(salvo) : null;
  });

  // 2. Monitora mudanças em 'data' e salva no localStorage automaticamente
  useEffect(() => {
    if (data) {
      localStorage.setItem("prospeccao_data", JSON.stringify(data));
    }
  }, [data]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!setor.trim() || !regiao.trim()) {
      setError("Preencha setor e região.");
      return;
    }

    setLoading(true);
    setData(null);
    localStorage.removeItem("prospeccao_data"); // Limpa o cache antigo antes da nova busca

    try {
      const result = await searchProspects({
        setor: setor.trim(),
        regiao: regiao.trim(),
        maxResultados: Number(maxResultados) || 30,
      });
      setData(result);
    } catch (err) {
      setError(err.message || "Falha na busca.");
    } finally {
      setLoading(false);
    }
  }

  const results = data?.results ?? [];
  const temSite = (c) => Boolean((c.website || "").trim());
  const resultsFiltrados = results.filter((c) => {
    if (filtroSite === "com") return temSite(c);
    if (filtroSite === "sem") return !temSite(c);
    return true;
  });

  return (
    <div className="page">
      <header>
        <h1>Prospecção Rápida</h1>
        <p className="subtitle">Toque no nome para copiar. Toque no telefone para abrir o WhatsApp.</p>
      </header>

      <form className="filters" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="setor">Setor</label>
          <input
            id="setor"
            list="setores"
            value={setor}
            onChange={(e) => setSetor(e.target.value)}
            placeholder="ex.: clínicas"
            autoComplete="off"
          />
          <datalist id="setores">
            {SETORES.map((s) => <option key={s} value={s} />)}
          </datalist>
        </div>

        <div className="field">
          <label htmlFor="regiao">Região</label>
          <input
            id="regiao"
            list="regioes"
            value={regiao}
            onChange={(e) => setRegiao(e.target.value)}
            placeholder="ex.: Itapevi"
            autoComplete="off"
          />
          <datalist id="regioes">
            {REGIOES.map((r) => <option key={r} value={r} />)}
          </datalist>
        </div>

        <div className="filter-group-row">
          <div className="field field-small">
            <label htmlFor="max">Máx.</label>
            <input
              id="max"
              type="number"
              min="1"
              max="100"
              value={maxResultados}
              onChange={(e) => setMaxResultados(e.target.value)}
            />
          </div>

          <div className="field field-select">
            <label htmlFor="filtro">Site</label>
            <select id="filtro" value={filtroSite} onChange={(e) => setFiltroSite(e.target.value)}>
              <option value="todos">Todos</option>
              <option value="com">Com site</option>
              <option value="sem">Sem site</option>
            </select>
          </div>
        </div>

        <button type="submit" className="btn-submit" disabled={loading}>
          {loading ? "Buscando…" : "Pesquisar"}
        </button>
      </form>

      {error && <div className="alert error">{error}</div>}

      {loading && (
        <div className="alert info">
          Coletando dados em background... Aguarde.
        </div>
      )}

      {data && !loading && (
        <ResultsList
          results={resultsFiltrados}
          total={results.length}
          filtroSite={filtroSite}
          setor={data.setor}
          regiao={data.regiao}
        />
      )}
    </div>
  );
}

function ResultsList({ results, total, filtroSite }) {
  const [copiadoId, setCopiadoId] = useState(null);
  const filtroLabel = filtroSite === "com" ? "com site" : filtroSite === "sem" ? "sem site" : null;

  if (results.length === 0) {
    return (
      <div className="alert info">
        Nenhuma empresa encontrada para os critérios informados.
      </div>
    );
  }

  const handleCopy = async (texto, index) => {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiadoId(index);
      setTimeout(() => setCopiadoId(null), 1500);
    } catch (err) {
      console.error("Erro ao copiar: ", err);
    }
  };

  return (
    <>
      <p className="count">
        {results.length} {filtroLabel ? `de ${total}` : ""} resultados encontrados.
      </p>
      
      <div className="list-container">
        {/* MODO DESKTOP */}
        <div className="desktop-table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Empresa (Clique p/ copiar)</th>
                <th>WhatsApp</th>
                <th>Endereço</th>
                <th>Website</th>
                <th>Maps</th>
              </tr>
            </thead>
            <tbody>
              {results.map((c, i) => {
                const wa = toWhatsappLink(c.telefone);
                return (
                  <tr key={`dt-${c.empresa}-${i}`}>
                    <td>{i + 1}</td>
                    <td 
                      className={`td-copyable ${copiadoId === `dt-${i}` ? "copied" : ""}`}
                      onClick={() => handleCopy(c.empresa || "", `dt-${i}`)}
                    >
                      <div className="td-name-flex">
                        <span className="truncate-text-desktop">{c.empresa || "—"}</span>
                        <span className="copy-mini-badge">{copiadoId === `dt-${i}` ? "Copiado!" : "Copiar"}</span>
                      </div>
                    </td>
                    <td>
                      {wa ? (
                        <a className="wa-link" href={wa} target="_blank" rel="noreferrer">{c.telefone}</a>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td className="td-address">{c.endereco || <span className="muted">—</span>}</td>
                    <td>
                      {c.website ? (
                        <a href={c.website} target="_blank" rel="noreferrer">site</a>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      {c.url_maps ? (
                        <a href={c.url_maps} target="_blank" rel="noreferrer">ver</a>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* MODO MOBILE */}
        <div className="mobile-cards-wrap">
          {results.map((c, i) => {
            const wa = toWhatsappLink(c.telefone);
            return (
              <div className="mobile-card" key={`mb-${c.empresa}-${i}`}>
                <div 
                  className={`col-name ${copiadoId === `mb-${i}` ? "copied" : ""}`} 
                  onClick={() => handleCopy(c.empresa || "", `mb-${i}`)}
                >
                  <span className="mobile-label">Empresa:</span>
                  <div className="name-wrapper">
                    <span className="text-truncate">{c.empresa || "—"}</span>
                    <span className="copy-badge">{copiadoId === `mb-${i}` ? "Copiado!" : "Copiar"}</span>
                  </div>
                </div>

                <div className="col-phone">
                  <span className="mobile-label">WhatsApp:</span>
                  {wa ? (
                    <a className="wa-link" href={wa} target="_blank" rel="noreferrer">{c.telefone}</a>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </div>

                <div className="col-site">
                  <span className="mobile-label">Website:</span>
                  {c.website ? (
                    <a href={c.website} className="site-link" target="_blank" rel="noreferrer">Acessar Site</a>
                  ) : (
                    <span className="muted">Sem site</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}