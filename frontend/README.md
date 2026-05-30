# Frontend — Prospecção de Empresas

Workspace separado (React + Vite) que consome a API do backend FastAPI deste
projeto. O usuário escolhe **setor** e **região** (combobox: dá pra escolher na
lista ou digitar), define o máximo de resultados, pesquisa e recebe uma tabela
com os dados das empresas. O telefone vira um link do **WhatsApp Web** (`wa.me`).

## Pré-requisitos

- Node 18+ (testado com Node 24)
- O backend rodando (na raiz do projeto):
  ```bash
  uvicorn app.main:app --reload
  # API em http://localhost:8000
  ```

## Rodar

```bash
cd frontend
npm install
npm run dev
# abre em http://localhost:5173
```

## Configuração da API

Por padrão o frontend chama `http://localhost:8000` (o backend tem CORS
liberado). Para apontar para outro endereço, crie `frontend/.env.local`:

```
VITE_API_BASE=http://localhost:8000
```

Alternativa sem CORS: use o proxy do Vite definido em `vite.config.js`
(`/api` → `:8000`) configurando `VITE_API_BASE=/api`.

## Endpoint consumido

`GET /prospect/search?setor=...&regiao=...&max_resultados=30`

Resposta:

```json
{
  "setor": "clínicas",
  "regiao": "Itapevi",
  "total": 2,
  "results": [
    {
      "empresa": "Clínica Exemplo",
      "endereco": "Rua X, 123",
      "telefone": "(11) 99999-9999",
      "website": "https://...",
      "url_maps": "https://www.google.com/maps/place/...",
      "cidade": "Itapevi",
      "setor_busca": "clínicas"
    }
  ]
}
```
