"""
Clona repositorios Java e executa a ferramenta CK.
"""

import os
import csv
import subprocess
import shutil as shutil_exec
from pathlib import Path

BASE_PROJETO = Path(__file__).resolve().parent.parent
PASTA_RESULTADOS = BASE_PROJETO / "resultados"
PASTA_CSVS = PASTA_RESULTADOS / "csvs"
PASTA_REPOS = PASTA_RESULTADOS / "repos"

SAIDA_SUMARIO = str(PASTA_CSVS / "resumo_metricas.csv")
PASTA_SAIDA_CK = "saida_ck"
ARQUIVO_CK_CLASSE = "class.csv"
USAR_JARS_PADRAO = "false"
MAX_ARQUIVOS_POR_PARTICAO = "0"
IMPRIMIR_VARIAVEIS_E_CAMPOS = "false"


def clonar_repositorio(nome_completo, destino):
    """Clona um repositorio no formato owner/repo para o destino informado."""
    url = f"https://github.com/{nome_completo}.git"
    subprocess.check_call(["git", "clone", "--depth", "1", url, str(destino)])


def executar_ck_no_caminho(caminho):
    """Executa CK no caminho e retorna o CSV de classes gerado.

    Usa o JAR apontado por `JAR_CK` quando presente; caso contrario,
    espera o comando `ck` disponivel no PATH.
    """
    ck_jar = os.environ.get("JAR_CK")
    pasta_saida = Path(caminho) / PASTA_SAIDA_CK
    pasta_saida.mkdir(parents=True, exist_ok=True)
    if ck_jar and Path(ck_jar).exists():
        cmd = [
            "java", "-jar", ck_jar,
            str(caminho),
            USAR_JARS_PADRAO,
            MAX_ARQUIVOS_POR_PARTICAO,
            IMPRIMIR_VARIAVEIS_E_CAMPOS,
            str(pasta_saida),
        ]
    else:
        if not shutil_exec.which("ck"):
            raise SystemExit(
                "Nao foi possivel encontrar o comando 'ck'. "
                "Defina JAR_CK no .env com o caminho do JAR do CK ou instale o comando ck no PATH."
            )
        cmd = [
            "ck",
            str(caminho),
            USAR_JARS_PADRAO,
            MAX_ARQUIVOS_POR_PARTICAO,
            IMPRIMIR_VARIAVEIS_E_CAMPOS,
            str(pasta_saida),
        ]
    print("Executando:", " ".join(cmd))
    subprocess.check_call(cmd)
    arquivo_classes = pasta_saida / ARQUIVO_CK_CLASSE
    if arquivo_classes.exists():
        return arquivo_classes

    # Fallback: CK pode gerar arquivos com prefixo no diretorio raiz do repo.
    arquivo_prefixo = Path(caminho) / f"{PASTA_SAIDA_CK}{ARQUIVO_CK_CLASSE}"
    if arquivo_prefixo.exists():
        return arquivo_prefixo

    raise SystemExit("Arquivo class.csv nao encontrado na saida do CK")


def agregar_csv_ck(caminho_csv):
    """Agrega o CSV do CK e retorna estatisticas por metrica.

    Retorna um dicionario com media, mediana e desvio padrao
    populacional para CBO, DIT e LCOM.
    """
    import statistics
    with open(caminho_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cbo_vals = []
        dit_vals = []
        lcom_vals = []
        for r in reader:
            def obter_num(chaves):
                for k in chaves:
                    if k in r and r[k] not in (None, ""):
                        try:
                            return float(r[k])
                        except:
                            return None
                return None
            cbo = obter_num(["CBO","cbo"])
            dit = obter_num(["DIT","dit"])
            lcom = obter_num(["LCOM","lcom"])
            if cbo is not None:
                cbo_vals.append(cbo)
            if dit is not None:
                dit_vals.append(dit)
            if lcom is not None:
                lcom_vals.append(lcom)
    def estatisticas(arr):
        if not arr:
            return ("", "", "")
        return (statistics.mean(arr), statistics.median(arr), statistics.pstdev(arr))
    return {
        "CBO_media": estatisticas(cbo_vals)[0], "CBO_mediana": estatisticas(cbo_vals)[1], "CBO_desvio": estatisticas(cbo_vals)[2],
        "DIT_media": estatisticas(dit_vals)[0], "DIT_mediana": estatisticas(dit_vals)[1], "DIT_desvio": estatisticas(dit_vals)[2],
        "LCOM_media": estatisticas(lcom_vals)[0], "LCOM_mediana": estatisticas(lcom_vals)[1], "LCOM_desvio": estatisticas(lcom_vals)[2],
    }