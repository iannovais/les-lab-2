"""
Gera graficos de correlacao e tabela de correlacoes a partir de resumo_metricas.csv.
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE_PROJETO = Path(__file__).resolve().parent.parent
PASTA_RESULTADOS = BASE_PROJETO / "resultados"
PASTA_CSVS = PASTA_RESULTADOS / "csvs"
PASTA_GRAFICOS = PASTA_RESULTADOS / "graficos"

ARQUIVO_RESUMO = PASTA_CSVS / "resumo_metricas.csv"
ARQUIVO_CORR = PASTA_CSVS / "correlacoes.csv"

QUALIDADE_COLS = ["CBO_media", "DIT_media", "LCOM_media"]
PROCESSO_COLS = {
    "popularidade": "estrelas",
    "maturidade": "idade_anos",
    "atividade": "releases",
    "tamanho_loc": "loc",
    "tamanho_comentarios": "comentarios",
}


def carregar_dados():
    if not ARQUIVO_RESUMO.exists():
        raise SystemExit(f"Arquivo nao encontrado: {ARQUIVO_RESUMO}")
    df = pd.read_csv(ARQUIVO_RESUMO)
    num_cols = list(QUALIDADE_COLS) + list(PROCESSO_COLS.values())
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def gerar_grafico(df, x_col, y_col, titulo, saida):
    dados = df[[x_col, y_col]].dropna()
    if dados.empty:
        return False
    plt.figure(figsize=(7, 5))
    sns.scatterplot(data=dados, x=x_col, y=y_col, alpha=0.4, s=18)
    sns.regplot(data=dados, x=x_col, y=y_col, scatter=False, color="#333333", line_kws={"linewidth": 1})
    plt.title(titulo)
    plt.tight_layout()
    plt.savefig(saida, dpi=150)
    plt.close()
    return True


def gerar_correlacoes(df):
    linhas = []
    for proc_nome, x_col in PROCESSO_COLS.items():
        if x_col not in df.columns:
            continue
        for y_col in QUALIDADE_COLS:
            if y_col not in df.columns:
                continue
            sub = df[[x_col, y_col]].dropna()
            if len(sub) < 2:
                continue
            linhas.append({
                "processo": proc_nome,
                "x_col": x_col,
                "qualidade": y_col,
                "pearson": sub[x_col].corr(sub[y_col], method="pearson"),
                "spearman": sub[x_col].corr(sub[y_col], method="spearman"),
                "n": len(sub),
            })
    if linhas:
        pd.DataFrame(linhas).to_csv(ARQUIVO_CORR, index=False)


def main():
    df = carregar_dados()
    PASTA_GRAFICOS.mkdir(parents=True, exist_ok=True)

    for proc_nome, x_col in PROCESSO_COLS.items():
        if x_col not in df.columns:
            continue
        for y_col in QUALIDADE_COLS:
            if y_col not in df.columns:
                continue
            titulo = f"{proc_nome}: {x_col} vs {y_col}"
            saida = PASTA_GRAFICOS / f"{proc_nome}_{x_col}_{y_col}.png"
            gerar_grafico(df, x_col, y_col, titulo, saida)

    gerar_correlacoes(df)
    print(f"Graficos em: {PASTA_GRAFICOS}")
    print(f"Correlacoes em: {ARQUIVO_CORR}")


if __name__ == "__main__":
    main()
