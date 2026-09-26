```python
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ============================================================
# ÁGORA DA GEOPOLÍTICA - TSE 2026
# Atualização de candidatos via DivulgaCandContas
# ============================================================

VERSAO = "3.0.0"

BASE = "https://divulgacandcontas.tse.jus.br/divulga/rest/v1"

ELEICAO = "20322002026"
ANO = "2026"

UF = os.environ.get("UF", "PB").upper()

OUT = "dados"

os.makedirs(OUT, exist_ok=True)


# ============================================================
# CÓDIGOS DOS CARGOS
# ============================================================

CARGOS = {
    "PRESIDENTE": 1,
    "GOVERNADOR": 3,
    "SENADOR": 5,
    "DEPUTADO FEDERAL": 6,
    "DEPUTADO ESTADUAL": 7,
}


# ============================================================
# CABEÇALHOS HTTP
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/153.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://divulgacandcontas.tse.jus.br/",
    "Origin": "https://divulgacandcontas.tse.jus.br",
    "Connection": "close",
}


# ============================================================
# REQUISIÇÃO À API
# ============================================================

def requisitar(url, tentativas=5):

    print()
    print("GET:", url)

    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):

        print(
            f"Tentativa {tentativa}/{tentativas}"
        )

        req = Request(
            url,
            headers=HEADERS,
            method="GET"
        )

        try:

            with urlopen(
                req,
                timeout=90
            ) as resposta:

                status = resposta.status

                dados = resposta.read()

                print(
                    "HTTP:",
                    status
                )

                print(
                    "Bytes:",
                    len(dados)
                )

                if status != 200:

                    raise RuntimeError(
                        f"HTTP inesperado: {status}"
```
