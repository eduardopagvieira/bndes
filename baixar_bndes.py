"""
Baixa os arquivos do conjunto "Operações de financiamento" do portal de dados abertos do BNDES.

O portal usa CKAN, então o script pergunta à API quais arquivos existem no conjunto
e baixa os CSV. Assim não depende de links fixos, que mudam quando o BNDES atualiza a base.

Uso:
    python baixar_bndes.py           # lista e baixa
    python baixar_bndes.py --listar  # só lista o que existe
"""

import argparse
import gzip
import shutil
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


def tamanho_remoto(sessao, url):
    r = sessao.head(url, timeout=60, allow_redirects=True)
    r.raise_for_status()
    return int(r.headers.get("Content-Length", 0))


def baixar(sessao, url, destino):
    """Baixa com retomada. O servidor às vezes fecha a conexão no meio sem dar erro,
    então o script confere o tamanho publicado e continua de onde parou (cabeçalho Range).
    CSVs são guardados compactados em gzip para economizar disco."""
    compactar = destino.suffix.lower() == ".csv"
    final = destino.with_name(destino.name + ".gz") if compactar else destino
    if final.exists() and final.stat().st_size > 0:
        print(f"  já existe, pulando: {final.name}")
        return
    total = tamanho_remoto(sessao, url)
    parcial = destino.with_name(destino.name + ".parcial")
    print(f"  baixando {destino.name} ({total / 1e6:.1f} MB)")
    for tentativa in range(1, 21):
        tem = parcial.stat().st_size if parcial.exists() else 0
        if total and tem >= total:
            break
        if tem:
            print(f"  retomando em {tem / 1e6:.1f} MB (tentativa {tentativa})")
        try:
            cabecalho = {"Range": f"bytes={tem}-"} if tem else {}
            with sessao.get(url, stream=True, timeout=300, headers=cabecalho) as r:
                r.raise_for_status()
                if tem and r.status_code != 206:
                    raise SystemExit("o servidor não aceita retomada (Range)")
                with open(parcial, "ab") as f:
                    for bloco in r.iter_content(1024 * 1024):
                        f.write(bloco)
        except requests.RequestException as erro:
            print(f"  conexão caiu: {erro}")
            time.sleep(5)
        if not total:
            break
    tem = parcial.stat().st_size
    if total and tem != total:
        raise SystemExit(f"download incompleto: {tem} de {total} bytes")
    if compactar:
        print("  compactando em gzip")
        with open(parcial, "rb") as origem, gzip.open(final, "wb", compresslevel=6) as saida:
            shutil.copyfileobj(origem, saida, 16 * 1024 * 1024)
        parcial.unlink()
    else:
        parcial.replace(final)
    print(f"  ok: {final.name}, {final.stat().st_size / 1e6:.1f} MB no disco")


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
