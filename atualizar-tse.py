```text
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

VERSAO = "3.1.0"

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
    "Accept-Language": (
        "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
    "Referer": (
        "https://divulgacandcontas.tse.jus.br/"
    ),
    "Origin": (
        "https://divulgacandcontas.tse.jus.br"
    ),
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
                    )

                if not dados:

                    raise RuntimeError(
                        "Resposta vazia da API."
                    )

                try:

                    texto = dados.decode(
                        "utf-8"
                    )

                except UnicodeDecodeError:

                    texto = dados.decode(
                        "latin-1",
                        errors="replace"
                    )

                try:

                    return json.loads(
                        texto
                    )

                except json.JSONDecodeError as erro:

                    trecho = texto[:500]

                    raise RuntimeError(
                        "A resposta do TSE "
                        "não contém JSON válido. "
                        f"Resposta: {trecho}"
                    ) from erro

        except HTTPError as erro:

            ultimo_erro = erro

            corpo = ""

            try:

                corpo = erro.read().decode(
                    "utf-8",
                    errors="replace"
                )[:1000]

            except Exception:
                pass

            print(
                f"HTTP {erro.code}"
            )

            if corpo:

                print(
                    "Resposta do servidor:",
                    corpo
                )

            codigos_retry = {
                403,
                429,
                500,
                502,
                503,
                504,
            }

            if erro.code not in codigos_retry:

                raise RuntimeError(
                    f"HTTP {erro.code}"
                )

        except URLError as erro:

            ultimo_erro = erro

            print(
                "Erro de rede:",
                erro.reason
            )

        except Exception as erro:

            ultimo_erro = erro

            print(
                "Erro:",
                erro
            )

        if tentativa < tentativas:

            espera = tentativa * 4

            print(
                f"Aguardando {espera} segundos..."
            )

            time.sleep(
                espera
            )

    raise RuntimeError(
        "Não foi possível acessar a API "
        f"após {tentativas} tentativas. "
        f"Último erro: {ultimo_erro}"
    )


# ============================================================
# BUSCAR CANDIDATOS
# ============================================================

def buscar_candidatos(
    unidade,
    codigo_cargo
):

    url = (
        f"{BASE}/candidatura/listar/"
        f"{ANO}/"
        f"{unidade}/"
        f"{ELEICAO}/"
        f"{codigo_cargo}/"
        f"candidatos"
    )

    return requisitar(url)


# ============================================================
# EXTRAIR LISTA DE CANDIDATOS
# ============================================================

def extrair_lista(resposta):

    if isinstance(
        resposta,
        list
    ):

        return resposta

    if isinstance(
        resposta,
        dict
    ):

        possibilidades = [
            "candidatos",
            "content",
            "data",
            "items",
        ]

        for chave in possibilidades:

            valor_chave = resposta.get(
                chave
            )

            if isinstance(
                valor_chave,
                list
            ):

                return valor_chave

    raise RuntimeError(
        "Formato de resposta do TSE "
        "não reconhecido."
    )


# ============================================================
# OBTER VALOR DE FORMA SEGURA
# ============================================================

def valor(
    objeto,
    *chaves
):

    if not isinstance(
        objeto,
        dict
    ):

        return ""

    for chave in chaves:

        if (
            chave in objeto
            and objeto[chave] is not None
        ):

            return objeto[chave]

    return ""


# ============================================================
# NORMALIZAR CANDIDATO
# ============================================================

def normalizar(
    candidato,
    cargo_nome,
    unidade
):

    cargo_obj = (
        candidato.get("cargo")
        if isinstance(
            candidato.get("cargo"),
            dict
        )
        else {}
    )

    partido_obj = (
        candidato.get("partido")
        if isinstance(
            candidato.get("partido"),
            dict
        )
        else {}
    )

    return {

        "id": str(
            valor(
                candidato,
                "id",
                "sq_CANDIDATO"
            )
        ),

        "uf": str(
            valor(
                candidato,
                "ufCandidatura",
                "sg_UE"
            )
            or unidade
        ).upper(),

        "cargo": str(
            valor(
                candidato,
                "ds_CARGO",
                "descricaoCargo"
            )
            or valor(
                cargo_obj,
                "descricao",
                "nome"
            )
            or cargo_nome
        ),

        "codigo_cargo": (
            cargo_obj.get("codigo")
            or CARGOS[cargo_nome]
        ),

        "numero": str(
            valor(
                candidato,
                "numero",
                "nr_CANDIDATO"
            )
        ),

        "nome": str(
            valor(
                candidato,
                "nomeCompleto",
                "nm_CANDIDATO"
            )
        ),

        "nome_urna": str(
            valor(
                candidato,
                "nomeUrna",
                "nm_URNA"
            )
        ),

        "nome_social": str(
            valor(
                candidato,
                "nomeSocial"
            )
        ),

        "partido": str(
            valor(
                candidato,
                "nm_PARTIDO"
            )
            or valor(
                partido_obj,
                "nome"
            )
        ),

        "sigla_partido": str(
            valor(
                candidato,
                "sg_PARTIDO"
            )
            or valor(
                partido_obj,
                "sigla"
            )
        ),

        "numero_partido": str(
            valor(
                partido_obj,
                "numero"
            )
        ),

        "situacao": str(
            valor(
                candidato,
                "descricaoSituacao",
                "situacaoCandidato"
            )
        ),

        "situacao_totalizacao": str(
            valor(
                candidato,
                "descricaoTotalizacao"
            )
        ),

        "foto": str(
            valor(
                candidato,
                "fotoUrl",
                "urlFoto"
            )
        ),

        "id_superior": str(
            valor(
                candidato,
                "idCandidatoSuperior",
                "sq_CANDIDATO_SUPERIOR"
            )
        ),
    }


# ============================================================
# SALVAR JSON COM SEGURANÇA
# ============================================================

def salvar(
    nome,
    dados
):

    caminho = os.path.join(
        OUT,
        nome
    )

    temporario = (
        caminho + ".tmp"
    )

    with open(
        temporario,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            separators=(",", ":")
        )

    os.replace(
        temporario,
        caminho
    )

    try:

        quantidade = len(
            dados
        )

    except TypeError:

        quantidade = 1

    print(
        f"Gerado: {caminho} "
        f"-> {quantidade} registros"
    )


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():

    inicio = datetime.now(
        timezone.utc
    )

    print()
    print("=" * 70)
    print("ÁGORA DA GEOPOLÍTICA - TSE 2026")
    print("ATUALIZAÇÃO DE CANDIDATOS")
    print("=" * 70)

    print(
        "Versão:",
        VERSAO
    )

    print(
        "Eleição:",
        ELEICAO
    )

    print(
        "Ano:",
        ANO
    )

    print(
        "UF:",
        UF
    )

    print(
        "API:",
        BASE
    )

    print()
    print(
        "Fonte utilizada:"
    )

    print(
        "Tribunal Superior Eleitoral "
        "- DivulgaCandContas"
    )

    print()
    print(
        "Este script NÃO utiliza:"
    )

    print(
        "consulta_cand_2026.zip"
    )

    print()
    print(
        "Iniciando consultas..."
    )

    # --------------------------------------------------------
    # TAREFAS
    # --------------------------------------------------------

    tarefas = [

        (
            "BR",
            "PRESIDENTE"
        ),

        (
            UF,
            "GOVERNADOR"
        ),

        (
            UF,
            "SENADOR"
        ),

        (
            UF,
            "DEPUTADO FEDERAL"
        ),

        (
            UF,
            "DEPUTADO ESTADUAL"
        ),
    ]

    todos = []

    resultados = {}

    falhas = []

    # --------------------------------------------------------
    # CONSULTAR CADA CARGO
    # --------------------------------------------------------

    for unidade, cargo_nome in tarefas:

        codigo = CARGOS[
            cargo_nome
        ]

        print()
        print("-" * 70)

        print(
            f"CARGO:
```
