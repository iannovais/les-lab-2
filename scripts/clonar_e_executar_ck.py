"""
Clona um repositório (ou lê de um CSV em português) e executa a ferramenta CK.

Requisitos:
 - `git` no PATH
 - Java + JAR do CK (defina `JAR_CK`) ou comando `ck` disponível

Saída:
 - `resumo_metricas.csv` com médias/medianas/desvios para CBO, DIT, LCOM por repositório
"""

import os
import csv
import shutil
import os as os_exec
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
    url = f"https://github.com/{nome_completo}.git"
    subprocess.check_call(["git", "clone", "--depth", "1", url, str(destino)])


def executar_ck_no_caminho(caminho):
    """Executa CK no caminho e retorna o caminho do CSV de classes gerado."""
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

    # fallback: CK pode gerar arquivos com prefixo no diretorio raiz do repo
    arquivo_prefixo = Path(caminho) / f"{PASTA_SAIDA_CK}{ARQUIVO_CK_CLASSE}"
    if arquivo_prefixo.exists():
        return arquivo_prefixo

    raise SystemExit("Arquivo class.csv nao encontrado na saida do CK")


def agregar_csv_ck(caminho_csv):
    """Agrega o CSV do CK e retorna dicionário com media/mediana/desvio para CBO, DIT, LCOM."""
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


def escrever_resumo_saida(arquivo_saida, nome_repo, stats):
    existe = Path(arquivo_saida).exists()
    with open(arquivo_saida, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ["repositorio","CBO_media","CBO_mediana","CBO_desvio","DIT_media","DIT_mediana","DIT_desvio","LCOM_media","LCOM_mediana","LCOM_desvio"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not existe:
            writer.writeheader()
        linha = {"repositorio": nome_repo}
        linha.update({k: stats.get(k, "") for k in fieldnames if k != "repositorio"})
        writer.writerow(linha)


def processar_repositorio(nome_repo, arquivo_saida=SAIDA_SUMARIO):
    """Clona, executa CK e grava o resumo para o repositório informado."""
    PASTA_REPOS.mkdir(parents=True, exist_ok=True)
    PASTA_CSVS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_REPOS / nome_repo.replace('/', '_')
    if destino.exists():
        print(f"Removendo pasta existente {destino}")
        def _onerror(func, path, exc_info):
            try:
                os_exec.chmod(path, 0o700)
                func(path)
            except Exception:
                pass
        shutil.rmtree(destino, onerror=_onerror)
    destino.parent.mkdir(parents=True, exist_ok=True)
    print(f"Clonando {nome_repo} em {destino}")
    clonar_repositorio(nome_repo, destino)

    try:
        csv_ck = executar_ck_no_caminho(destino)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Falha ao executar CK: {e}")

    estat = agregar_csv_ck(csv_ck)
    escrever_resumo_saida(arquivo_saida, nome_repo, estat)
    print(f"Resumo gravado em {arquivo_saida}")


def processar_repositorio_por_csv(caminho_csv, index=0, arquivo_saida=SAIDA_SUMARIO):
    """Lê o CSV (coluna `nome_completo`) e processa o repositório no índice fornecido."""
    with open(caminho_csv, newline='', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        if index < 0 or index >= len(reader):
            raise SystemExit("Índice fora do intervalo no CSV")
        nome_repo = reader[index]["nome_completo"]
    processar_repositorio(nome_repo, arquivo_saida=arquivo_saida)
