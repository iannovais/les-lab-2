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
import time
import re
from datetime import datetime, timezone
from pathlib import Path
import requests

BASE_PROJETO = Path(__file__).resolve().parent.parent
PASTA_RESULTADOS = BASE_PROJETO / "resultados"
PASTA_CSVS = PASTA_RESULTADOS / "csvs"
PASTA_REPOS = PASTA_RESULTADOS / "repos"

SAIDA_SUMARIO = str(PASTA_CSVS / "resumo_metricas.csv")
PASTA_SAIDA_CK = "saida_ck"
ARQUIVO_CK_CLASSE = "class.csv"
USAR_JARS_PADRAO = "false"
MAX_ARQUIVOS_POR_PARTICAO = "100"
IMPRIMIR_VARIAVEIS_E_CAMPOS = "false"
ARQUIVO_FALHAS = str(PASTA_CSVS / "falhas.csv")

TENTATIVAS_MAXIMAS = 5
ESPERA_BASE_SEGUNDOS = 30


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


def escrever_resumo_saida(arquivo_saida, linha):
    caminho = Path(arquivo_saida)
    fieldnames = [
        "repositorio",
        "estrelas",
        "forks",
        "criado_em",
        "atualizado_em",
        "idade_anos",
        "releases",
        "loc",
        "comentarios",
        "CBO_media",
        "CBO_mediana",
        "CBO_desvio",
        "DIT_media",
        "DIT_mediana",
        "DIT_desvio",
        "LCOM_media",
        "LCOM_mediana",
        "LCOM_desvio",
    ]
    repo = linha.get("repositorio")
    if caminho.exists() and repo:
        with open(caminho, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        atualizado = False
        for r in rows:
            if r.get("repositorio") == repo:
                for k in fieldnames:
                    r[k] = linha.get(k, "")
                atualizado = True
                break
        if atualizado:
            with open(caminho, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    writer.writerow({k: r.get(k, "") for k in fieldnames})
            return
    with open(arquivo_saida, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not caminho.exists() or caminho.stat().st_size == 0:
            writer.writeheader()
        writer.writerow({k: linha.get(k, "") for k in fieldnames})


def escrever_falha(arquivo_falhas, nome_repo, motivo):
    existe = Path(arquivo_falhas).exists()
    with open(arquivo_falhas, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["repositorio", "motivo"])
        if not existe:
            writer.writeheader()
        writer.writerow({"repositorio": nome_repo, "motivo": motivo})


def calcular_idade_anos(criado_em_iso):
    if not criado_em_iso:
        return ""
    try:
        dt = datetime.fromisoformat(criado_em_iso.replace("Z", "+00:00"))
    except Exception:
        return ""
    agora = datetime.now(timezone.utc)
    return round((agora - dt).days / 365.25, 4)


def normalizar_resumo(arquivo_saida):
    caminho = Path(arquivo_saida)
    if not caminho.exists():
        return
    campos_novos = [
        "repositorio",
        "estrelas",
        "forks",
        "criado_em",
        "atualizado_em",
        "idade_anos",
        "releases",
        "loc",
        "comentarios",
        "CBO_media",
        "CBO_mediana",
        "CBO_desvio",
        "DIT_media",
        "DIT_mediana",
        "DIT_desvio",
        "LCOM_media",
        "LCOM_mediana",
        "LCOM_desvio",
    ]
    campos_antigos = [
        "repositorio",
        "CBO_media",
        "CBO_mediana",
        "CBO_desvio",
        "DIT_media",
        "DIT_mediana",
        "DIT_desvio",
        "LCOM_media",
        "LCOM_mediana",
        "LCOM_desvio",
    ]
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    if not linhas:
        return
    dados = {}
    for idx, linha in enumerate(linhas):
        if idx == 0:
            continue
        partes = [p.strip() for p in linha.split(",")]
        if len(partes) == len(campos_novos):
            row = dict(zip(campos_novos, partes))
        elif len(partes) == len(campos_antigos):
            row = dict(zip(campos_antigos, partes))
        else:
            continue
        repo = row.get("repositorio")
        if not repo:
            continue
        if repo in dados:
            atual = dados[repo]
            def preenchidos(r):
                return sum(1 for v in r.values() if v not in (None, ""))
            if preenchidos(row) <= preenchidos(atual):
                continue
        dados[repo] = row
    if not dados:
        return
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos_novos)
        writer.writeheader()
        for repo, row in dados.items():
            writer.writerow({k: row.get(k, "") for k in campos_novos})


def obter_total_releases(nome_repo, token=None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    tentativa = 0
    url = f"https://api.github.com/repos/{nome_repo}/releases"
    params = {"per_page": 1, "page": 1}
    while True:
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 200:
            break
        if resp.status_code == 404:
            return 0
        if resp.status_code == 403 and tentativa < TENTATIVAS_MAXIMAS:
            texto = resp.text.lower()
            if "secondary rate limit" in texto or "rate limit exceeded" in texto:
                espera = ESPERA_BASE_SEGUNDOS * (2 ** tentativa)
                print(f"Rate limit detectado. Aguardando {espera}s e tentando novamente...")
                time.sleep(espera)
                tentativa += 1
                continue
        raise SystemExit(f"Erro na API do GitHub {resp.status_code}: {resp.text}")
    itens = resp.json()
    if not itens:
        return 0
    link = resp.headers.get("Link", "")
    if 'rel="last"' in link:
        m = re.search(r"[&?]page=(\d+)>; rel=\"last\"", link)
        if m:
            return int(m.group(1))
    return len(itens)


def contar_loc_comentarios(caminho_repo):
    loc = 0
    comentarios = 0
    ignorar = {".git", "target", "build", "out", "node_modules"}
    for raiz, dirs, arquivos in os.walk(caminho_repo):
        dirs[:] = [d for d in dirs if d not in ignorar and not d.startswith(".")]
        for nome in arquivos:
            if not nome.endswith(".java"):
                continue
            caminho = Path(raiz) / nome
            try:
                with open(caminho, encoding="utf-8", errors="ignore") as f:
                    in_block = False
                    for linha in f:
                        original = linha
                        linha = linha.rstrip("\n")
                        if not linha.strip() and not in_block:
                            continue
                        i = 0
                        tem_codigo = False
                        tem_comentario = False
                        while i < len(linha):
                            if in_block:
                                fim = linha.find("*/", i)
                                tem_comentario = True
                                if fim == -1:
                                    break
                                i = fim + 2
                                in_block = False
                                continue
                            pos_line = linha.find("//", i)
                            pos_block = linha.find("/*", i)
                            candidatos = [p for p in [pos_line, pos_block] if p != -1]
                            if not candidatos:
                                if linha[i:].strip():
                                    tem_codigo = True
                                break
                            prox = min(candidatos)
                            if linha[i:prox].strip():
                                tem_codigo = True
                            if prox == pos_line:
                                tem_comentario = True
                                break
                            tem_comentario = True
                            in_block = True
                            i = prox + 2
                        if tem_codigo:
                            loc += 1
                        if tem_comentario:
                            comentarios += 1
            except Exception:
                continue
    return loc, comentarios


def processar_repositorio(nome_repo, info_repo=None, token=None, arquivo_saida=SAIDA_SUMARIO, manter_repo=True):
    """Clona, executa CK e grava o resumo com metricas de processo e qualidade."""
    PASTA_REPOS.mkdir(parents=True, exist_ok=True)
    PASTA_CSVS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_REPOS / nome_repo.replace('/', '_')
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        print(f"Clonando {nome_repo} em {destino}")
        clonar_repositorio(nome_repo, destino)
    else:
        print(f"Usando repo existente {destino}")

    try:
        csv_ck = executar_ck_no_caminho(destino)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Falha ao executar CK: {e}")

    estat = agregar_csv_ck(csv_ck)
    loc, comentarios = contar_loc_comentarios(destino)
    releases = obter_total_releases(nome_repo, token=token)
    info_repo = info_repo or {}
    linha = {
        "repositorio": nome_repo,
        "estrelas": info_repo.get("estrelas", ""),
        "forks": info_repo.get("forks", ""),
        "criado_em": info_repo.get("criado_em", ""),
        "atualizado_em": info_repo.get("atualizado_em", ""),
        "idade_anos": calcular_idade_anos(info_repo.get("criado_em")),
        "releases": releases,
        "loc": loc,
        "comentarios": comentarios,
    }
    linha.update(estat)
    escrever_resumo_saida(arquivo_saida, linha)
    print(f"Resumo gravado em {arquivo_saida}")

    if not manter_repo:
        def _onerror(func, path, exc_info):
            try:
                os_exec.chmod(path, 0o700)
                func(path)
            except Exception:
                pass
        shutil.rmtree(destino, onerror=_onerror)


def processar_repositorio_por_csv(caminho_csv, index=0, arquivo_saida=SAIDA_SUMARIO, token=None, manter_repo=True):
    """Le o CSV (coluna `nome_completo`) e processa o repositorio no indice fornecido."""
    with open(caminho_csv, newline='', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        if index < 0 or index >= len(reader):
            raise SystemExit("Indice fora do intervalo no CSV")
        info_repo = reader[index]
        nome_repo = info_repo["nome_completo"]
    processar_repositorio(nome_repo, info_repo=info_repo, token=token, arquivo_saida=arquivo_saida, manter_repo=manter_repo)


def carregar_resumo_existente(arquivo_saida):
    normalizar_resumo(arquivo_saida)
    if not Path(arquivo_saida).exists():
        return set()
    with open(arquivo_saida, newline='', encoding='utf-8') as f:
        return {r.get("repositorio") for r in csv.DictReader(f) if r.get("repositorio")}


def processar_repositorios_em_lote(caminho_csv, inicio=0, fim=None, arquivo_saida=SAIDA_SUMARIO, token=None, manter_repo=True, pular_existentes=True, arquivo_falhas=ARQUIVO_FALHAS):
    """Processa varios repositorios listados no CSV."""
    with open(caminho_csv, newline='', encoding='utf-8') as f:
        repos = list(csv.DictReader(f))
    if fim is None or fim > len(repos):
        fim = len(repos)
    existentes = carregar_resumo_existente(arquivo_saida) if pular_existentes else set()
    for i in range(inicio, fim):
        info_repo = repos[i]
        nome_repo = info_repo.get("nome_completo")
        if not nome_repo:
            continue
        if nome_repo in existentes:
            print(f"Pulando {nome_repo} (ja processado)")
            continue
        try:
            print(f"Processando {i - inicio + 1}/{fim - inicio}: {nome_repo}")
            processar_repositorio(nome_repo, info_repo=info_repo, token=token, arquivo_saida=arquivo_saida, manter_repo=manter_repo)
        except Exception as e:
            print(f"Falha ao processar {nome_repo}: {e}")
            escrever_falha(arquivo_falhas, nome_repo, str(e))
