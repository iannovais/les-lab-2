"""
Buscar os repositórios Java mais populares no GitHub ordenados por estrelas.
"""

import csv
import time
import requests


ITENS_POR_PAGINA_PADRAO = 100
MAX_REPOS_PADRAO = 1000
TENTATIVAS_MAXIMAS = 5
ESPERA_BASE_SEGUNDOS = 30


def buscar_repos_java(saida, itens_por_pagina=ITENS_POR_PAGINA_PADRAO, max_repos=MAX_REPOS_PADRAO, token=None):
    """Busca os repositórios Java mais populares no GitHub e grava em CSV.

    O CSV usa colunas em português para facilitar o processamento:
    nome_completo, url_html, estrelas, forks, criado_em, atualizado_em.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    repos = []
    # Calcula o numero de paginas necessario para cobrir o maximo solicitado.
    paginas = (max_repos + itens_por_pagina - 1) // itens_por_pagina
    for pagina in range(1, paginas + 1):
        params = {
            "q": "language:Java",
            "sort": "stars",
            "order": "desc",
            "per_page": itens_por_pagina,
            "page": pagina,
        }
        tentativa = 0
        while True:
            resp = requests.get("https://api.github.com/search/repositories", headers=headers, params=params)
            if resp.status_code == 200:
                break
            # Aplica backoff exponencial quando o limite de requisicoes e atingido.
            if resp.status_code == 403 and tentativa < TENTATIVAS_MAXIMAS:
                texto = resp.text.lower()
                if "secondary rate limit" in texto or "rate limit exceeded" in texto:
                    espera = ESPERA_BASE_SEGUNDOS * (2 ** tentativa)
                    print(f"Rate limit detectado. Aguardando {espera}s e tentando novamente...")
                    time.sleep(espera)
                    tentativa += 1
                    continue
            raise SystemExit(f"Erro na API do GitHub {resp.status_code}: {resp.text}")
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        for it in items:
            repos.append({
                "nome_completo": it.get("full_name"),
                "url_html": it.get("html_url"),
                "estrelas": it.get("stargazers_count"),
                "forks": it.get("forks_count"),
                "criado_em": it.get("created_at"),
                "atualizado_em": it.get("updated_at"),
            })
            
        # Pausa curta entre paginas para reduzir chance de rate limit.
        time.sleep(1)
        
        if len(repos) >= max_repos:
            break

    repos = repos[:max_repos]
    with open(saida, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["nome_completo","url_html","estrelas","forks","criado_em","atualizado_em"])
        writer.writeheader()
        for r in repos:
            writer.writerow(r)
    print(f"Gravado {len(repos)} repositórios em {saida}")
