# CTribNac API

> API pública com os 326 Códigos de Tributação Nacional (cTribNac) da Lista Nacional de Serviços (LC 116/2003), usados na emissão de NFS-e pelo Sistema Nacional (SEFIN).

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Deploy](https://img.shields.io/badge/deploy-Vercel-black.svg)](https://ctribnac.nfsemonitor.com.br)

**Base URL:** `https://ctribnac.nfsemonitor.com.br`

## O que é o cTribNac?

O `cTribNac` é o campo obrigatório na DPS (Declaração de Prestação de Serviço) que identifica o serviço prestado conforme a Lista Nacional de Serviços da LC 116/2003. Sem ele, não é possível emitir uma NFS-e pelo Sistema Nacional (SEFIN).

## Endpoints

### Buscar por texto ou código

```
GET /codigos?q={busca}
```

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `q` | string | Sim | Texto ou código a buscar |
| `limite` | int | Não | Máximo de resultados (padrão: 20, máximo: 100) |

A busca funciona com:
- **Texto parcial:** `contab` encontra `Contabilidade`
- **Sem acento:** `programacao` encontra `Programação`
- **Múltiplos termos (AND):** `limpeza imovel` retorna só os que contêm ambas as palavras
- **Código exato:** `171901`

**Exemplos:**

```bash
curl https://ctribnac.nfsemonitor.com.br/codigos?q=contabilidade
curl https://ctribnac.nfsemonitor.com.br/codigos?q=programacao
curl https://ctribnac.nfsemonitor.com.br/codigos?q=010101
curl https://ctribnac.nfsemonitor.com.br/codigos?q=limpeza&limite=5
```

**Resposta:**

```json
{
  "total": 1,
  "limite": 20,
  "q": "contabilidade",
  "codigos": [
    {
      "codigo": "171901",
      "descricao": "Contabilidade, inclusive serviços técnicos e auxiliares."
    }
  ]
}
```

---

### Buscar código específico

```
GET /codigos/{codigo}
```

```bash
curl https://ctribnac.nfsemonitor.com.br/codigos/171901
```

```json
{
  "codigo": "171901",
  "descricao": "Contabilidade, inclusive serviços técnicos e auxiliares."
}
```

---

### Documentação interativa

```
GET /docs
```

Documentação completa com Redoc.

## Rodando localmente

```bash
git clone https://github.com/matheuscardosos/nfse-codigos-api
cd nfse-codigos-api
pip install -r requirements.txt
uvicorn api.index:app --reload
```

Acesse `http://localhost:8000`.

## Fonte dos dados

Extraído do **ANEXO I - SEFIN ADN DPS NFS-e v1.00 (dez/2025)**, planilha oficial do Sistema Nacional NFS-e, disponível em [gov.br/nfse](https://www.gov.br/nfse).

## Contribuindo

Encontrou um código desatualizado ou faltando? Edite `codigos.json` e abra um PR. Toda contribuição é bem-vinda.

## Licença

MIT - veja [LICENSE](LICENSE).
