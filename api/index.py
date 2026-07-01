import json
import unicodedata
import re
import time
from collections import defaultdict
from pathlib import Path
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.openapi.docs import get_redoc_html

ROOT = Path(__file__).parent
with open(ROOT / "codigos.json", encoding="utf-8") as f:
    CODIGOS = json.load(f)

# Rate limiting em memoria: 60 requisicoes por minuto por IP
LIMITE_RPM = 60
_contadores: dict = defaultdict(list)

def checar_rate_limit(ip: str) -> bool:
    agora = time.time()
    _contadores[ip] = [t for t in _contadores[ip] if agora - t < 60]
    if len(_contadores[ip]) >= LIMITE_RPM:
        return False
    _contadores[ip].append(agora)
    return True

DESCRICAO_API = """\
API pública com os **326 Códigos de Tributação Nacional (cTribNac)** \
da Lista Nacional de Serviços (LC 116/2003), usados na emissão de NFS-e \
pelo Sistema Nacional (SEFIN).

Busca por código ou descrição, com suporte a texto sem acento e busca parcial.

---

**Uso justo:** esta API é pública e gratuita, mas não foi feita para chamadas \
em loop ou scraping massivo. Limite: **60 requisições por minuto por IP**. \
Se precisar de todos os dados de uma vez, baixe o arquivo JSON completo: \
[/codigos.json](/codigos.json)

Se precisar de volume alto em produção, hospede sua própria instância - \
o código é MIT e está no GitHub.

---

Licença: **MIT**\
"""

app = FastAPI(
    title="CTribNac API",
    description=DESCRICAO_API,
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)

@app.get("/public/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ROOT / "public" / "favicon.ico", media_type="image/x-icon")

@app.get("/public/vercel.svg", include_in_schema=False)
def vercel_svg():
    return FileResponse(ROOT / "public" / "vercel.svg", media_type="image/svg+xml")


def normalizar(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto.lower())
    sem_acento = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", sem_acento).strip()


def ip_do_request(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return HTMLResponse(PAGINA_INICIAL)


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
def redoc():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="CTribNac API - Documentacao",
        redoc_favicon_url="/public/favicon.ico",
    )


@app.get(
    "/codigos.json",
    summary="Download completo",
    description="Retorna todos os 326 códigos em um único arquivo JSON. Ideal para quem quer manter uma cópia local e evitar chamadas repetidas à API.",
    response_description="Lista completa de códigos de tributação nacional",
)
def download_json():
    return FileResponse(ROOT / "codigos.json", media_type="application/json", filename="ctribnac-codigos.json")


@app.get(
    "/codigos",
    summary="Buscar códigos de tributação",
    description="""\
Busca códigos de tributação nacional por código ou descrição.

- Busca parcial: `contab` encontra `Contabilidade`
- Sem acento: `programacao` encontra `Programação`
- Múltiplos termos (AND): `limpeza imovel` retorna só os que contêm ambas as palavras
- Por código: `171901` retorna exatamente esse código

**Limite:** 60 requisições por minuto por IP. Para acesso massivo, baixe o \
arquivo completo em [/codigos.json](/codigos.json).\
""",
    response_description="Lista de códigos encontrados",
)
def buscar_codigos(
    request: Request,
    q: str = Query(..., description="Texto ou código a buscar", examples=["contabilidade"]),
    limite: int = Query(20, ge=1, le=100, description="Máximo de resultados (padrão 20, máximo 100)"),
):
    if not checar_rate_limit(ip_do_request(request)):
        return JSONResponse(
            {"erro": "Limite de requisições atingido (60/min). Aguarde um minuto ou baixe o JSON completo em /codigos.json."},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    q_strip = q.strip()

    # busca progressiva por codigo: so digitos -> startswith
    if re.fullmatch(r"\d{1,6}", q_strip):
        codigo_prefixo = q_strip.zfill(6) if len(q_strip) == 6 else q_strip
        if len(q_strip) == 6:
            resultado = [item for item in CODIGOS if item["codigo"] == codigo_prefixo][:limite]
        else:
            resultado = [item for item in CODIGOS if item["codigo"].startswith(q_strip)][:limite]
    else:
        termos = normalizar(q_strip).split()
        if not termos:
            return JSONResponse({"erro": "Parâmetro q inválido."}, status_code=400)
        resultado = [
            item for item in CODIGOS
            if all(
                any(palavra.startswith(t) for palavra in normalizar(item["descricao"]).split())
                for t in termos
            )
        ][:limite]

    return {
        "total": len(resultado),
        "limite": limite,
        "q": q,
        "codigos": resultado,
    }


@app.get(
    "/codigos/{codigo}",
    summary="Buscar código específico",
    description="Retorna um código de tributação nacional pelo código exato de 6 dígitos.",
)
def buscar_codigo(request: Request, codigo: str):
    if not checar_rate_limit(ip_do_request(request)):
        return JSONResponse(
            {"erro": "Limite de requisições atingido (60/min). Aguarde um minuto ou baixe o JSON completo em /codigos.json."},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    item = next((c for c in CODIGOS if c["codigo"] == codigo.zfill(6)), None)
    if not item:
        return JSONResponse({"erro": f"Código '{codigo}' não encontrado."}, status_code=404)
    return item


PAGINA_INICIAL = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CTribNac API</title>
  <link rel="icon" href="/public/favicon.ico">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f0f6fd;
      color: #0f1923;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    main {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 64px 24px 48px;
      text-align: center;
    }
    .kicker {
      font-size: .72rem;
      font-weight: 700;
      letter-spacing: .14em;
      text-transform: uppercase;
      color: #0078d4;
      margin-bottom: 18px;
    }
    h1 {
      font-size: clamp(2.2rem, 5vw, 3.2rem);
      font-weight: 800;
      letter-spacing: -.04em;
      line-height: 1.05;
      color: #0f1923;
    }
    .sub {
      margin-top: 18px;
      font-size: 1.05rem;
      color: #3a5068;
      max-width: 460px;
      line-height: 1.65;
    }
    .actions {
      margin-top: 40px;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      justify-content: center;
    }
    .btn {
      display: inline-block;
      padding: 12px 26px;
      border-radius: 8px;
      text-decoration: none;
      font-weight: 600;
      font-size: .95rem;
      transition: filter .15s;
    }
    .btn:hover { filter: brightness(.9); }
    .btn-primary { background: #0078d4; color: #fff; }
    .btn-secondary { background: #fff; color: #0078d4; border: 1.5px solid #c7dff7; }
    .snippet {
      margin-top: 56px;
      background: #fff;
      border: 1px solid #c7dff7;
      border-radius: 10px;
      padding: 20px 24px;
      font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
      font-size: .82rem;
      color: #3a5068;
      text-align: left;
      max-width: 460px;
      width: 100%;
      line-height: 1.8;
    }
    .snippet .comment { color: #7fa8c9; }
    .snippet .url { color: #0078d4; }
    footer {
      padding: 28px 24px;
      text-align: center;
      font-size: .8rem;
      color: #7fa8c9;
      border-top: 1px solid #c7dff7;
    }
    footer a { color: #0078d4; text-decoration: none; }
    footer a:hover { text-decoration: underline; }
    .vercel-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      margin-top: 8px;
      font-size: .78rem;
      color: #7fa8c9;
    }
    .vercel-badge img { height: 18px; opacity: .5; vertical-align: middle; }
  </style>
</head>
<body>
  <main>
    <p class="kicker">API pública e gratuita</p>
    <h1>CTribNac API</h1>
    <p class="sub">Os 326 Códigos de Tributação Nacional da LC 116/2003, disponíveis para consulta na emissão de NFS-e pelo Sistema Nacional (SEFIN).</p>

    <div class="actions">
      <a href="/docs" class="btn btn-primary">Ver documentação</a>
      <a href="/codigos.json" class="btn btn-secondary">Baixar JSON completo</a>
    </div>

    <div class="snippet">
      <span class="comment"># busca por texto</span><br>
      GET <span class="url">/codigos?q=contabilidade</span><br><br>
      <span class="comment"># busca progressiva por código</span><br>
      GET <span class="url">/codigos?q=1719</span><br><br>
      <span class="comment"># código exato</span><br>
      GET <span class="url">/codigos/171901</span><br><br>
      <span class="comment"># todos os 326 códigos em JSON</span><br>
      GET <span class="url">/codigos.json</span>
    </div>
  </main>

  <footer>
    Mantido por <a href="https://nfsemonitor.com.br">NFS-e Monitor</a> &nbsp;·&nbsp; <a href="https://github.com/matheuscardosos/nfse-codigos-api">GitHub</a>
    <br>
    <span class="vercel-badge">
      Hospedado na <img src="/public/vercel.svg" alt="Vercel">
    </span>
  </footer>
</body>
</html>"""
