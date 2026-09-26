import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "https://divulgacandcontas.tse.jus.br/divulga/rest/v1"
ELEICAO = "20322002026"
ANO = "2026"

# Códigos de cargo usados pelo sistema de candidaturas do TSE:
# 1 Presidente, 3 Governador, 5 Senador,
# 6 Deputado Federal, 7 Deputado Estadual/Distrital.
CARGOS = {
    "PRESIDENTE": 1,
    "GOVERNADOR": 3,
    "SENADOR": 5,
    "DEPUTADO FEDERAL": 6,
    "DEPUTADO ESTADUAL": 7,
}

UF = os.environ.get("UF", "PB").upper()

OUT = "dados"
os.makedirs(OUT, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AgoraDaGeopolitica-TSE2026/1.0)",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://divulgacandcontas.tse.jus.br/",
    "Origin": "https://divulgacandcontas.tse.jus.br",
}


def requisitar(url):
    print("\nGET", url)

    req = Request(url, headers=HEADERS, method="GET")

    try:
        with urlopen(req, timeout=60) as response:
            status = response.status
            data = response.read()

            print("HTTP:", status)
            print("Bytes:", len(data))

            if status != 200:
                raise RuntimeError(f"HTTP {status}")

            try:
                return json.loads(data.decode("utf-8"))
            except UnicodeDecodeError:
                return json.loads(data.decode("latin-1"))

    except HTTPError as e:
        corpo = ""
        try:
            corpo = e.read().decode("utf-8", errors="replace")[:1000]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} - {corpo}")

    except URLError as e:
        raise RuntimeError(f"Erro de rede: {e.reason}")


def buscar_candidatos(unidade, cargo_codigo):
    # O endpoint oficial do DivulgaCandContas usa a unidade eleitoral
    # no lugar do município nas eleições gerais de 2026.
    url = (
        f"{BASE}/candidatura/listar/"
        f"{ANO}/{unidade}/{ELEICAO}/{cargo_codigo}/candidatos"
    )

    return requisitar(url)


def extrair_lista(resposta):
    if isinstance(resposta, list):
        return resposta

    if isinstance(resposta, dict):
        for chave in ("candidatos", "content", "data", "items"):
            valor = resposta.get(chave)
            if isinstance(valor, list):
                return valor

    return []


def valor(obj, *chaves):
    if not isinstance(obj, dict):
        return ""

    for chave in chaves:
        if chave in obj and obj[chave] is not None:
            return obj[chave]

    return ""


def normalizar(c, cargo_nome, unidade):
    cargo_obj = c.get("cargo") if isinstance(c.get("cargo"), dict) else {}
    partido_obj = c.get("partido") if isinstance(c.get("partido"), dict) else {}

    return {
        "id": str(valor(c, "id", "sq_CANDIDATO")),
        "uf": str(valor(c, "ufCandidatura", "sg_UE") or unidade).upper(),
        "cargo": str(
            valor(c, "ds_CARGO", "descricaoCargo")
            or valor(cargo_obj, "descricao", "nome")
            or cargo_nome
        ),
        "codigo_cargo": cargo_obj.get("codigo") or CARGOS[cargo_nome],
        "numero": str(valor(c, "numero", "nr_CANDIDATO")),
        "nome": str(valor(c, "nomeCompleto", "nm_CANDIDATO")),
        "nome_urna": str(valor(c, "nomeUrna", "nm_URNA")),
        "nome_social": str(valor(c, "nomeSocial")),
        "partido": str(
            valor(c, "nm_PARTIDO")
            or valor(partido_obj, "nome")
        ),
        "sigla_partido": str(
            valor(c, "sg_PARTIDO")
            or valor(partido_obj, "sigla")
        ),
        "numero_partido": str(
            valor(partido_obj, "numero")
        ),
        "situacao": str(
            valor(c, "descricaoSituacao", "situacaoCandidato")
        ),
        "situacao_totalizacao": str(
            valor(c, "descricaoTotalizacao")
        ),
        "foto": str(
            valor(c, "fotoUrl", "urlFoto")
        ),
        "id_superior": str(
            valor(c, "idCandidatoSuperior", "sq_CANDIDATO_SUPERIOR")
        ),
    }


def salvar(nome, dados):
    caminho = os.path.join(OUT, nome)

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(
            dados,
            f,
            ensure_ascii=False,
            separators=(",", ":")
        )

    print("Gerado:", caminho, "->", len(dados), "registros")


def main():
    print("=" * 60)
    print("ÁGORA DA GEOPOLÍTICA - API TSE / DIVULGACANDCONTAS")
    print("=" * 60)
    print("Eleição:", ELEICAO)
    print("UF:", UF)

    todos = []

    # Presidente é nacional.
    tarefas = [
        ("BR", "PRESIDENTE"),
        (UF, "GOVERNADOR"),
        (UF, "SENADOR"),
        (UF, "DEPUTADO FEDERAL"),
        (UF, "DEPUTADO ESTADUAL"),
    ]

    resultados = {}

    for unidade, cargo_nome in tarefas:
        codigo = CARGOS[cargo_nome]

        try:
            resposta = buscar_candidatos(unidade, codigo)
            lista = extrair_lista(resposta)

            normalizados = [
                normalizar(c, cargo_nome, unidade)
                for c in lista
            ]

            # Remove registros sem ID.
            normalizados = [
                c for c in normalizados if c["id"]
            ]

            resultados[cargo_nome] = normalizados
            todos.extend(normalizados)

            print(
                f"{cargo_nome}: {len(normalizados)} candidatos"
            )

        except Exception as e:
            print(
                f"FALHA em {cargo_nome}: {e}"
            )
            resultados[cargo_nome] = []

        time.sleep(0.5)

    if not todos:
        raise RuntimeError(
            "A API respondeu, mas nenhum candidato foi obtido."
        )

    # Remove duplicidades por ID.
    unicos = {}
    for candidato in todos:
        unicos[candidato["id"]] = candidato

    todos = list(unicos.values())

    # Arquivo completo.
    salvar("candidatos.json", todos)

    # Arquivos por cargo.
    for cargo_nome, lista in resultados.items():
        slug = (
            cargo_nome
            .lower()
            .replace(" ", "-")
            .replace("/", "-")
        )
        salvar(f"{slug}.json", lista)

    # Arquivo da UF, útil para a interface.
    salvar(f"{UF}.json", [
        c for c in todos
        if c["uf"] == UF or (
            c["cargo"] == "PRESIDENTE" and UF
        )
    ])

    status = {
        "fonte": "Tribunal Superior Eleitoral - DivulgaCandContas",
        "eleicao": ELEICAO,
        "ano": ANO,
        "uf": UF,
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "total": len(todos),
        "quantidades": {
            cargo: len(lista)
            for cargo, lista in resultados.items()
        },
        "api": BASE,
    }

    salvar("status.json", status)

    print("\n" + "=" * 60)
    print("ATUALIZAÇÃO CONCLUÍDA")
    print("=" * 60)
    print("Total:", len(todos))
    print(json.dumps(status["quantidades"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\nERRO FATAL:")
        print(str(e))
        sys.exit(1)
