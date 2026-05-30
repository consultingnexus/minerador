import { useState } from "react";
import { searchProspects } from "./api.js";
import { toWhatsappLink } from "./whatsapp.js";

// Sugestões dos comboboxes — o usuário pode escolher OU digitar livremente.
const SETORES = [
  "clínicas",
  "pet shops",
  "oficinas mecânicas",
  "restaurantes",
  "academias",
  "salões de beleza",
  "dentistas",
  "escritórios de advocacia",
  "imobiliárias",
  "contabilidade",
];

const REGIOES = [
  "Itapevi",
  "Barueri",
  "Osasco",
  "Carapicuíba",
  "Jandira",
  "Cotia",
  "São Paulo",
  "Santana de Parnaíba",
];

export default function App() {
  const [setor, setSetor] = useState("clínicas");
  const [regiao, setRegiao] = useState("Itapevi");
  const [maxResultados, setMaxResultados] = useState(30);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!setor.trim() || !regiao.trim()) {
      setError("Preencha setor e região.");
      return;
    }

    setLoading(true);
    setData(null);
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

  return (
    <div className="page">
      <header>
        <h1>Prospecção de Empresas</h1>
        <p className="subtitle">
          Busca no Google Maps por setor e região. Telefone vira link do
          WhatsApp.
        </p>
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
            {SETORES.map((s) => (
              <option key={s} value={s} />
            ))}
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
            {REGIOES.map((r) => (
              <option key={r} value={r} />
            ))}
          </datalist>
        </div>

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

        <button type="submit" disabled={loading}>
          {loading ? "Buscando…" : "Pesquisar"}
        </button>
      </form>

      {error && <div className="alert error">{error}</div>}

      {loading && (
        <div className="alert info">
          Coletando do Google Maps… isso pode levar alguns minutos.
        </div>
      )}

      {data && !loading && (
        <ResultsTable
          results={results}
          setor={data.setor}
          regiao={data.regiao}
        />
      )}
    </div>
  );
}

function ResultsTable({ results, setor, regiao }) {
  if (results.length === 0) {
    return (
      <div className="alert info">
        Nenhuma empresa encontrada para “{setor}” em “{regiao}”.
      </div>
    );
  }

  return (
    <>
      <p className="count">
        {results.length} empresa(s) — {setor} / {regiao}
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Empresa</th>
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
                <tr key={`${c.empresa}-${i}`}>
                  <td>{i + 1}</td>
                  <td>{c.empresa || "—"}</td>
                  <td>
                    {wa ? (
                      <a
                        className="wa-link"
                        href={wa}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {c.telefone}
                      </a>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>{c.endereco || <span className="muted">—</span>}</td>
                  <td>
                    {c.website ? (
                      <a href={c.website} target="_blank" rel="noreferrer">
                        site
                      </a>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>
                    {c.url_maps ? (
                      <a href={c.url_maps} target="_blank" rel="noreferrer">
                        ver
                      </a>
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
    </>
  );
}
