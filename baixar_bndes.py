"""
Baixa os arquivos do conjunto "Operações de financiamento" do portal de dados abertos do BNDES.

O portal usa CKAN, então o script pergunta à API quais arquivos existem no conjunto
e baixa os CSV. Assim não depende de links fixos, que mudam quando o BNDES atualiza a base.

Uso:
    python baixar_bndes.py           # lista e baixa
    python baixar_bndes.py --listar  # só lista o que existe
"""

import argparse
import time
from pathlib import Path

import requests

API = "https://dadosabertos.bndes.gov.br/api/3/action/package_show"
CONJUNTO = "operacoes-financiamento"
PASTA = Path("dados/brutos")


def listar(sessao):
    r = sessao.get(API, params={"id": CONJUNTO}, timeout=60)
    r.raise_for_status()
    recursos = r.json()["result"]["resources"]
    print(f"{len(recursos)} arquivos no conjunto {CONJUNTO}")
    for rec in recursos:
        print(f"- {rec.get('name')} | {rec.get('format')} | {rec.get('url')}")
    return recursos


def baixar(sessao, url, destino):
    if destino.exists() and destino.stat().st_size > 0:
        print(f"  já existe, pulando: {destino.name}")
        return
    print(f"  baixando {destino.name}")
    with sessao.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        temporario = destino.with_suffix(destino.suffix + ".parcial")
        with open(temporario, "wb") as f:
            for bloco in r.iter_content(1024 * 1024):
                f.write(bloco)
        temporario.replace(destino)
    print(f"  ok: {destino.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--listar", action="store_true")
    args = parser.parse_args()

    sessao = requests.Session()
    sessao.headers["User-Agent"] = "portfolio-bndes (pesquisa academica)"
    recursos = listar(sessao)
    if args.listar:
        raise SystemExit

    PASTA.mkdir(parents=True, exist_ok=True)
    for rec in recursos:
        url = rec.get("url", "")
        formato = (rec.get("format") or "").upper()
        if formato not in ("CSV", "PDF") and not url.lower().endswith((".csv", ".pdf")):
            continue                               # CSV = dados, PDF = dicionário de dados
        nome = url.rstrip("/").split("/")[-1] or f"{rec['id']}.csv"
        baixar(sessao, url, PASTA / nome)
        time.sleep(1)
    print("Fim")
