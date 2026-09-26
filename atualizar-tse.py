import json
import os
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

VERSAO = "4.0.0"

BASE = "https://divulgacandcontas.tse.jus.br/divulga/rest/v1"
ELEICAO = "20322002026"
ANO = "2026"

UF = os.environ.get("UF", "PB").upper()

OUT = "dados"

CARGOS = {
"PRESIDENTE": 1,
"GOVERNADOR": 3,
"SENADOR": 5,
"DEPUTADO FEDERAL": 6,
"DEPUTADO ESTADUAL": 7,
}

HEADERS = {
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
"Accept": "application/json, text/plain, */*",
"Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
"Referer": "https://divulgacandcontas.tse.jus.br/",
"Origin": "https://divulgacandcontas.tse.jus.br",
}

def requisitar(url, tentativas=5):
"""Faz uma requisição HTTP ao DivulgaCandContas."""

```
ultimo_erro = None

for tentativa in range(1, tentativas + 1):
    try:
        print(f"  Requisição {tentativa}/{tentativas}")

        request = Request(url, headers=HEADERS, method="GET")

        with urlopen(request, timeout=60) as resposta:
            conteudo = resposta.read().decode("utf-8")

        return json.loads(conteudo)

    except HTTPError as erro:
        ultimo_erro = erro

        print(
            f"  HTTP {erro.code}: {erro.reason}"
        )

        if erro.code not in (403, 429, 500, 502, 503, 504):
            raise

    except (URLError, TimeoutError, json.JSONDecodeError) as erro:
        ultimo_erro = erro
        print(f"  Erro: {erro}")

    if tentativa < tentativas:
        espera = tentativa * 5
        print(f"  Aguardando {espera} segundos...")
        time.sleep(espera)

raise RuntimeError(
    f"Não foi possível acessar o TSE após {tentativas} tentativas: {ultimo_erro}"
)
```

def buscar_candidatos(unidade, codigo_cargo):
"""Consulta os candidatos de uma unidade eleitoral."""

```
url = (
    f"{BASE}/candidatura/listar/"
    f"{ANO}/"
    f"{unidade}/"
    f"{ELEICAO}/"
    f"{codigo_cargo}/"
    f"candidatos"
)

print()
print(f"URL: {url}")

return requisitar(url)
```

def extrair_lista(resposta):
"""Extrai a lista de candidatos de diferentes formatos possíveis."""

```
if isinstance(resposta, list):
    return resposta

if not isinstance(resposta, dict):
    return []

for chave in ("candidatos", "content", "lista", "dados", "results"):
    valor = resposta.get(chave)

    if isinstance(valor, list):
        return valor

return []
```

def salvar(caminho, dados):
"""Salva JSON formatado em UTF-8."""

```
with open(caminho, "w", encoding="utf-8") as arquivo:
    json.dump(
        dados,
        arquivo,
        ensure_ascii=False,
        indent=2,
    )
```

def main():

```
print("=" * 60)
print("ÁGORA DA GEOPOLÍTICA - TSE 2026")
print("=" * 60)
print()
print(f"Versão: {VERSAO}")
print(f"UF: {UF}")
print(f"Eleição: {ELEICAO}")
print()
print("Fonte: DivulgaCandContas")
print("Esta versão NÃO utiliza o arquivo consulta_cand_2026.zip.")
print()

os.makedirs(OUT, exist_ok=True)

consultas = [
    ("BR", "PRESIDENTE"),
    (UF, "GOVERNADOR"),
    (UF, "SENADOR"),
    (UF, "DEPUTADO FEDERAL"),
    (UF, "DEPUTADO ESTADUAL"),
]

resultados = []
total = 0

for unidade, cargo in consultas:

    codigo = CARGOS[cargo]

    print("-" * 60)
    print(f"CARGO: {cargo}")
    print(f"UNIDADE: {unidade}")
    print(f"CÓDIGO: {codigo}")

    try:
        resposta = buscar_candidatos(unidade, codigo)

        candidatos = extrair_lista(resposta)

        quantidade = len(candidatos)

        print(f"Candidatos encontrados: {quantidade}")

        arquivo_cargo = (
            cargo.lower()
            .replace(" ", "_")
            .replace("ã", "a")
            .replace("é", "e")
        )

        caminho = os.path.join(
            OUT,
            f"{unidade.lower()}_{arquivo_cargo}.json"
        )

        salvar(caminho, candidatos)

        resultados.append(
            {
                "unidade": unidade,
                "cargo": cargo,
                "codigo": codigo,
                "quantidade": quantidade,
                "arquivo": caminho,
                "sucesso": True,
            }
        )

        total += quantidade

    except Exception as erro:

        print(f"ERRO no cargo {cargo}: {erro}")

        resultados.append(
            {
                "unidade": unidade,
                "cargo": cargo,
                "codigo": codigo,
                "quantidade": 0,
                "arquivo": None,
                "sucesso": False,
                "erro": str(erro),
            }
        )

agora = datetime.now(timezone.utc).isoformat()

candidatos_gerais = {
    "versao": VERSAO,
    "ano": ANO,
    "eleicao": ELEICAO,
    "uf": UF,
    "atualizado_em": agora,
    "total": total,
    "resultados": resultados,
}

salvar(
    os.path.join(OUT, "status.json"),
    candidatos_gerais,
)

print()
print("=" * 60)
print("RESUMO")
print("=" * 60)

for resultado in resultados:
    status = "OK" if resultado["sucesso"] else "ERRO"

    print(
        f"{status} | "
        f"{resultado['unidade']} | "
        f"{resultado['cargo']} | "
        f"{resultado['quantidade']}"
    )

print()
print(f"TOTAL DE CANDIDATOS: {total}")

if total == 0:
    raise RuntimeError(
        "Nenhum candidato foi encontrado. "
        "A atualização não será considerada válida."
    )

print()
print("Atualização concluída com sucesso.")
```

if **name** == "**main**":
main()
