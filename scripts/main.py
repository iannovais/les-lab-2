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
from clonar_e_executar_ck import processar_repositorio_por_csv

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
    p.add_argument('--index', type=int, default=0, help='índice (0-based) do repositório para medir')
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

    # clonar e executar CK no índice selecionado
    print(f'Processando repositório no índice {args.index}...')
    processar_repositorio_por_csv(args.saida_lista, index=args.index)

    print('Execução completa. Verifique resumo_metricas.csv')


if __name__ == '__main__':
    main()
