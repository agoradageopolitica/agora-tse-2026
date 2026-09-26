import csv
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from urllib.request import Request, urlopen


# ============================================================
# ÁGORA DA GEOPOLÍTICA
# Atualizador de candidatos - Eleições 2026
# ============================================================

TSE_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/"
    "consulta_cand/consulta_cand_2026.zip"
)

OUTPUT_DIR = "dados"


def baixar_arquivo(url):
    print("==============================================")
    print("ÁGORA DA GEOPOLÍTICA - TSE 2026")
    print("==============================================")
    print("URL:")
    print(url)
    print()
    print("Baixando arquivo do TSE...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/153 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Connection": "close",
    }

    request = Request(url, headers=headers)

    try:
        with urlopen(request, timeout=120) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            data = response.read()

            print("HTTP:", status)
            print("Content-Type:", content_type)
            print("Tamanho:", len(data), "bytes")

            if status != 200:
                raise RuntimeError(
                    f"O TSE respondeu com HTTP {status}."
                )

            if len(data) < 1000:
                raise RuntimeError(
                    "O arquivo recebido é muito pequeno. "
                    "Provavelmente não é o ZIP esperado."
                )

            return data

    except Exception as e:
        print()
        print("ERRO AO ACESSAR O TSE:")
        print(str(e))
        raise


def localizar_csv(zip_bytes):
    print()
    print("Analisando ZIP...")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        nomes = z.namelist()

        print("Arquivos encontrados:", len(nomes))

        candidatos = []

        for nome in nomes:
            nome_upper = nome.upper()

            if (
                nome_upper.endswith(".CSV")
                and "CONSULTA_CAND" in nome_upper
            ):
                candidatos.append(nome)

        if not candidatos:
            print()
            print("Arquivos CSV encontrados:")

            for nome in nomes:
                if nome.upper().endswith(".CSV"):
                    print(" -", nome)

            raise RuntimeError(
                "Não foi encontrado o CSV CONSULTA_CAND dentro do ZIP."
            )

        print()
        print("CSV selecionado:")
        print(candidatos[0])

        return z.read(candidatos[0])


def limpar(valor):
    if valor is None:
        return ""

    return str(valor).strip()


def encontrar_campo(row, nomes):
    for nome in nomes:
        if nome in row:
            return limpar(row[nome])

    return ""


def converter_csv(csv_bytes):
    print()
    print("Convertendo CSV...")

    # Arquivos eleitorais do TSE tradicionalmente utilizam
    # ISO-8859-1.
    texto = csv_bytes.decode("latin-1", errors="replace")

    primeira_linha = texto.splitlines()[0]

    if ";" in primeira_linha:
        delimitador = ";"
    elif "," in primeira_linha:
        delimitador = ","
    else:
        raise RuntimeError(
            "Não foi possível identificar o delimitador do CSV."
        )

    leitor = csv.DictReader(
        io.StringIO(texto),
        delimiter=delimitador
    )

    registros = []

    for linha in leitor:

        registro = {
            "id": encontrar_campo(
                linha,
                ["SQ_CANDIDATO"]
            ),

            "uf": encontrar_campo(
                linha,
                ["SG_UF"]
            ),

            "cargo": encontrar_campo(
                linha,
                ["DS_CARGO"]
            ),

            "codigo_cargo": encontrar_campo(
                linha,
                ["CD_CARGO"]
            ),

            "numero": encontrar_campo(
                linha,
                ["NR_CANDIDATO"]
            ),

            "nome": encontrar_campo(
                linha,
                ["NM_CANDIDATO"]
            ),

            "nome_urna": encontrar_campo(
                linha,
                ["NM_URNA_CANDIDATO"]
            ),

            "nome_social": encontrar_campo(
                linha,
                ["NM_SOCIAL_CANDIDATO"]
            ),

            "partido": encontrar_campo(
                linha,
                ["NM_PARTIDO"]
            ),

            "sigla_partido": encontrar_campo(
                linha,
                ["SG_PARTIDO"]
            ),

            "numero_partido": encontrar_campo(
                linha,
                ["NR_PARTIDO"]
            ),

            "federacao": encontrar_campo(
                linha,
                ["NM_FEDERACAO"]
            ),

            "sigla_federacao": encontrar_campo(
                linha,
                ["SG_FEDERACAO"]
            ),

            "situacao": encontrar_campo(
                linha,
                [
                    "DS_SITUACAO_CANDIDATURA",
                    "DS_SITUACAO_CANDIDATO_PLEITO"
                ]
            ),

            "detalhe_situacao": encontrar_campo(
                linha,
                [
                    "DS_DETALHE_SITUACAO_CAND",
                    "DS_DETALHE_SITUACAO_CANDIDATO"
                ]
            ),

            "inserido_urna": encontrar_campo(
                linha,
                ["ST_CANDIDATO_INSERIDO_URNA"]
            ),

            "foto": ""
        }

        # Não precisamos guardar linhas sem identificador.
        if not registro["id"]:
            continue

        registros.append(registro)

    print("Candidaturas encontradas:", len(registros))

    if not registros:
        raise RuntimeError(
            "O CSV foi lido, mas nenhuma candidatura foi encontrada."
        )

    return registros


def gerar_arquivos(registros):

    print()
    print("Gerando arquivos JSON...")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --------------------------------------------------------
    # Arquivo completo
    # --------------------------------------------------------

    caminho_completo = os.path.join(
        OUTPUT_DIR,
        "candidatos.json"
    )

    with open(
        caminho_completo,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            registros,
            arquivo,
            ensure_ascii=False,
            separators=(",", ":")
        )

    # --------------------------------------------------------
    # Arquivos por UF
    # --------------------------------------------------------

    por_uf = {}

    for candidato in registros:

        uf = candidato["uf"].upper()

        if not uf:
            continue

        por_uf.setdefault(uf, [])
        por_uf[uf].append(candidato)

    for uf, candidatos in por_uf.items():

        caminho = os.path.join(
            OUTPUT_DIR,
            f"{uf}.json"
        )

        with open(
            caminho,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                candidatos,
                arquivo,
                ensure_ascii=False,
                separators=(",", ":")
            )

    # --------------------------------------------------------
    # Arquivos por UF + cargo
    # --------------------------------------------------------

    por_uf_cargo = {}

    for candidato in registros:

        uf = candidato["uf"].upper()

        cargo = candidato["cargo"].upper()

        if not uf or not cargo:
            continue

        chave = (uf, cargo)

        por_uf_cargo.setdefault(chave, [])
        por_uf_cargo[chave].append(candidato)

    for (uf, cargo), candidatos in por_uf_cargo.items():

        cargo_slug = (
            cargo
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace("Á", "A")
            .replace("À", "A")
            .replace("Ã", "A")
            .replace("Â", "A")
            .replace("É", "E")
            .replace("Ê", "E")
            .replace("Í", "I")
            .replace("Ó", "O")
            .replace("Ô", "O")
            .replace("Õ", "O")
            .replace("Ú", "U")
            .replace("Ç", "C")
        )

        caminho = os.path.join(
            OUTPUT_DIR,
            f"{uf}-{cargo_slug}.json"
        )

        with open(
            caminho,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                candidatos,
                arquivo,
                ensure_ascii=False,
                separators=(",", ":")
            )

    # --------------------------------------------------------
    # Metadados
    # --------------------------------------------------------

    agora = datetime.now(
        timezone.utc
    ).isoformat()

    metadados = {
        "fonte": "Tribunal Superior Eleitoral",
        "eleicao": 2026,
        "atualizado_em": agora,
        "total_candidaturas": len(registros),
        "ufs": sorted(por_uf.keys()),
        "quantidade_ufs": len(por_uf),
        "arquivo_fonte": "consulta_cand_2026.zip"
    }

    with open(
        os.path.join(
            OUTPUT_DIR,
            "status.json"
        ),
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            metadados,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("==============================================")
    print("PROCESSAMENTO CONCLUÍDO")
    print("==============================================")
    print("Total:", len(registros))
    print("UFs:", len(por_uf))
    print("Atualização:", agora)
    print()


def main():

    try:

        zip_bytes = baixar_arquivo(TSE_URL)

        csv_bytes = localizar_csv(zip_bytes)

        registros = converter_csv(csv_bytes)

        gerar_arquivos(registros)

    except Exception as erro:

        print()
        print("==============================================")
        print("FALHA NA ATUALIZAÇÃO")
        print("==============================================")
        print(str(erro))
        print()

        sys.exit(1)


if __name__ == "__main__":
    main()
