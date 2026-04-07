"""
Runner principal `main.py` em português que orquestra todo o fluxo:
 - Carrega `.env` se existir
 - Busca os repositórios Java mais populares
 - Clona e executa CK no repositório selecionado

Uso:
  python main.py --saida-lista lista_repos.csv --index 0
"""

import os
import argparse
from pathlib import Path
from buscar_repos_java import buscar_repos_java
from clonar_e_executar_ck import processar_repositorio_por_csv, processar_repositorios_em_lote

BASE_PROJETO = Path(__file__).resolve().parent.parent
ARQUIVO_ENV = BASE_PROJETO / '.env'
PASTA_RESULTADOS = BASE_PROJETO / 'resultados'
PASTA_CSVS = PASTA_RESULTADOS / 'csvs'


def carregar_arquivo_env(caminho=ARQUIVO_ENV):
    if not caminho.exists():
        return
    with open(caminho, encoding='utf-8') as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith('#'):
                continue
            if '=' not in ln:
                continue
            k, v = ln.split('=', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--saida-lista', default=str(PASTA_CSVS / 'lista_repos_java.csv'))
    p.add_argument('--max', type=int, default=1000)
    p.add_argument('--index', type=int, default=0, help='indice (0-based) do repositorio para medir')
    p.add_argument('--lote', action='store_true', help='processar varios repositorios em sequencia')
    p.add_argument('--inicio', type=int, default=0, help='indice inicial (0-based) do lote')
    p.add_argument('--fim', type=int, default=None, help='indice final (exclusivo) do lote')
    p.add_argument('--reprocessar', action='store_true', help='reprocessar repos ja medidos no resumo')
    p.add_argument('--limpar-repos', action='store_true', help='remover repos clonados apos o processamento')
    p.add_argument('--forcar-lista', action='store_true', help='forçar nova coleta da lista de repositórios')
    args = p.parse_args()

    carregar_arquivo_env()

    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise SystemExit(
            "GITHUB_TOKEN nao encontrado. Preencha o .env com seu token e rode novamente."
        )

    # garantir pastas de resultados
    PASTA_CSVS.mkdir(parents=True, exist_ok=True)

    # gerar lista de repositórios
    if not Path(args.saida_lista).exists() or args.forcar_lista:
        print('Gerando lista de repositórios Java...')
        buscar_repos_java(args.saida_lista, max_repos=args.max, token=token)
    else:
        print('Usando lista existente de repositórios Java...')

    manter_repo = not args.limpar_repos
    modo_lote = args.lote or (args.inicio == 0 and args.fim is None and args.index == 0)
    if modo_lote:
        print(f'Processando repositorios em lote ({args.inicio} ate {args.fim})...')
        processar_repositorios_em_lote(
            args.saida_lista,
            inicio=args.inicio,
            fim=args.fim,
            token=token,
            manter_repo=manter_repo,
            pular_existentes=not args.reprocessar,
        )
    else:
        # clonar e executar CK no indice selecionado
        print(f'Processando repositorio no indice {args.index}...')
        processar_repositorio_por_csv(args.saida_lista, index=args.index, token=token, manter_repo=manter_repo)

    print('Execução completa. Verifique resumo_metricas.csv')


if __name__ == '__main__':
    main()
