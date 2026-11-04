"""
Limpa e junta as duas bases de operações do BNDES numa tabela só.

Entrada
    dados/brutos/operacoes-financiamento-operacoes-indiretas-automaticas.csv.gz
    dados/brutos/operacoes-financiamento-operacoes-nao-automaticas.csv.gz
Saída
    dados/tratados/operacoes.parquet          uma linha por operação, as duas bases juntas
    dados/tratados/nao_automaticas.parquet    só as não automáticas, com a descrição do projeto
    dados/auxiliares/ipca.csv                 índice do IPCA mensal (Banco Central, série 433)
    dados/auxiliares/populacao_uf.csv         população por UF no Censo 2022 (IBGE, tabela 4709)

Os valores ficam em reais correntes e também corrigidos pelo IPCA para o último mês com índice.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import requests

BRUTOS = Path("dados/brutos")
TRATADOS = Path("dados/tratados")
AUX = Path("dados/auxiliares")
AUTOMATICAS = BRUTOS / "operacoes-financiamento-operacoes-indiretas-automaticas.csv.gz"
NAO_AUTOMATICAS = BRUTOS / "operacoes-financiamento-operacoes-nao-automaticas.csv.gz"

# nomes das colunas na base automática -> nome comum
COMUNS = {
    "cliente": "cliente", "uf": "uf", "municipio": "municipio", "municipio_codigo": "municipio_codigo",
    "data_da_contratacao": "data", "valor_da_operacao_em_reais": "valor_contratado",
    "valor_desembolsado_reais": "valor_desembolsado", "fonte_de_recurso_desembolsos": "fonte_recurso",
    "custo_financeiro": "custo_financeiro", "juros": "juros", "prazo_carencia_meses": "carencia_meses",
    "prazo_amortizacao_meses": "amortizacao_meses", "modalidade_de_apoio": "modalidade",
    "forma_de_apoio": "forma_apoio", "produto": "produto", "instrumento_financeiro": "instrumento",
    "inovacao": "inovacao", "setor_cnae": "setor_cnae", "subsetor_cnae_agrupado": "subsetor_cnae",
    "subsetor_cnae_nome": "atividade_cnae", "setor_bndes": "setor", "subsetor_bndes": "subsetor",
    "porte_do_cliente": "porte", "natureza_do_cliente": "natureza",
    "instituicao_financeira_credenciada": "agente_financeiro", "situacao_da_operacao": "situacao",
}
# na base não automática alguns nomes mudam
NAO_AUTO_PARA_AUTO = {"valor_contratado_reais": "valor_da_operacao_em_reais",
                      "situacao_do_contrato": "situacao_da_operacao"}

SETORES = {"INFRA-ESTRUTURA": "Infraestrutura", "INFRAESTRUTURA": "Infraestrutura", "INDUSTRIA": "Indústria",
           "COMERCIO/SERVICOS": "Comércio e serviços", "AGROPECUÁRIA": "Agropecuária"}
PORTES = {"MICRO": "Micro", "PEQUENA": "Pequena", "MÉDIA": "Média", "GRANDE": "Grande"}
REGIOES = {
    "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
REGIAO_DA_UF = {uf: r for r, ufs in REGIOES.items() for uf in ufs}
UF_DO_CODIGO = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
                "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
                "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
                "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}


def numero(serie):
    """Os CSVs misturam inteiros e decimais com vírgula."""
    return pd.to_numeric(serie.str.strip().str.replace(",", ".", regex=False), errors="coerce")


def padronizar(bruto, origem):
    d = bruto.rename(columns=NAO_AUTO_PARA_AUTO)
    d = d[[c for c in COMUNS if c in d.columns]].rename(columns=COMUNS)
    for c in d.columns:
        d[c] = d[c].str.strip()
        d.loc[d[c].isin(["", "-", "----------"]), c] = np.nan
    for c in ["valor_contratado", "valor_desembolsado", "juros"]:
        d[c] = numero(d[c])
    for c in ["carencia_meses", "amortizacao_meses", "municipio_codigo"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").astype("Int64")
    d["data"] = pd.to_datetime(d["data"], format="%Y-%m-%d", errors="coerce")
    d["setor"] = d["setor"].map(SETORES)
    d["porte"] = d["porte"].map(PORTES)
    d["origem"] = origem
    return d


def ler_automaticas():
    """O arquivo tem mais de 2 milhões de linhas. Lido em blocos, só com as colunas usadas."""
    colunas = list(COMUNS)
    partes = []
    for i, bloco in enumerate(pd.read_csv(AUTOMATICAS, sep=";", encoding="latin1", dtype=str,
                                          usecols=colunas, chunksize=300_000)):
        partes.append(otimizar(padronizar(bloco, "Indireta automática")))
        print(f"  bloco {i + 1}: {sum(len(p) for p in partes):,} linhas")
    return concatenar(partes)


def otimizar(d):
    for c in d.columns:
        if d[c].dtype == object:
            d[c] = d[c].astype("category")
    return d


def concatenar(partes):
    """Concatena mantendo as colunas de texto como categoria (une as categorias de cada bloco)."""
    texto = [c for c in partes[0].columns if isinstance(partes[0][c].dtype, pd.CategoricalDtype)]
    for c in texto:
        todas = pd.api.types.union_categoricals([p[c] for p in partes]).categories
        for p in partes:
            p[c] = p[c].cat.set_categories(todas)
    return pd.concat(partes, ignore_index=True)


def ipca():
    destino = AUX / "ipca.csv"
    if not destino.exists():
        r = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados",
                         params={"formato": "json", "dataInicial": "01/01/2000", "dataFinal": "31/12/2030"},
                         timeout=60)
        r.raise_for_status()
        s = pd.DataFrame(r.json())
        s["mes"] = pd.to_datetime(s["data"], format="%d/%m/%Y").dt.to_period("M").astype(str)
        s["variacao"] = s["valor"].astype(float)
        s["indice"] = (1 + s["variacao"] / 100).cumprod()
        AUX.mkdir(parents=True, exist_ok=True)
        s[["mes", "variacao", "indice"]].to_csv(destino, index=False)
    return pd.read_csv(destino)


def populacao():
    destino = AUX / "populacao_uf.csv"
    if not destino.exists():
        r = requests.get("https://apisidra.ibge.gov.br/values/t/4709/n3/all/v/93/p/2022", timeout=60)
        r.raise_for_status()
        linhas = r.json()[1:]
        p = pd.DataFrame({"uf": [UF_DO_CODIGO[l["D1C"]] for l in linhas],
                          "populacao": [int(l["V"]) for l in linhas]})
        p.to_csv(destino, index=False)
    return pd.read_csv(destino)


def corrigir_pela_inflacao(d, indice):
    """Leva os valores para reais do último mês com IPCA. Contratos do mês corrente usam o último índice."""
    ultimo = indice["indice"].iloc[-1]
    fator = dict(zip(indice["mes"], ultimo / indice["indice"]))
    mes = d["data"].dt.to_period("M").astype(str)
    f = mes.map(fator).astype(float).fillna(1.0)
    d["valor_contratado_real"] = d["valor_contratado"] * f.to_numpy()
    d["valor_desembolsado_real"] = d["valor_desembolsado"] * f.to_numpy()
    return indice["mes"].iloc[-1]


def main():
    TRATADOS.mkdir(parents=True, exist_ok=True)
    indice = ipca()
    pop = populacao()
    print(f"IPCA até {indice['mes'].iloc[-1]}, população de {len(pop)} UFs")

    print("Lendo não automáticas")
    bruto_na = pd.read_csv(NAO_AUTOMATICAS, sep=";", encoding="latin1", dtype=str)
    na = padronizar(bruto_na, "Não automática")
    na["descricao"] = bruto_na["descricao_do_projeto"].str.strip().str.replace(r"\s+", " ", regex=True)
    na["numero_contrato"] = bruto_na["numero_do_contrato"].str.strip()
    print("Lendo indiretas automáticas")
    auto = ler_automaticas()

    ops = concatenar([otimizar(auto), otimizar(na.drop(columns=["descricao", "numero_contrato"]))])
    ops["origem"] = ops["origem"].astype("category")
    ops["ano"] = ops["data"].dt.year.astype("Int16")
    ops["uf"] = ops["uf"].astype(str).where(ops["uf"].astype(str).isin(REGIAO_DA_UF), np.nan).astype("category")
    ops["regiao"] = ops["uf"].map(REGIAO_DA_UF).astype("category")
    ops["psi"] = ops["instrumento"].astype(str).str.upper().str.startswith("PSI")
    ops["subsidio_tjlp"] = ops["custo_financeiro"].astype(str).str.startswith(("TJLP", "TJ4", "TJ6"))
    mes_base = corrigir_pela_inflacao(ops, indice)
    na_mes = corrigir_pela_inflacao(na, indice)

    # conferências
    print(f"\n{len(ops):,} operações, {ops['data'].min():%d/%m/%Y} a {ops['data'].max():%d/%m/%Y}")
    print(f"Valores corrigidos para reais de {mes_base}")
    print("Sem data:", ops["data"].isna().sum(), "| sem valor:", ops["valor_contratado"].isna().sum(),
          "| valor <= 0:", (ops["valor_contratado"] <= 0).sum(), "| sem UF válida:", ops["uf"].isna().sum())
    print("Setor sem classificação:", ops["setor"].isna().sum(), "| porte sem classificação:", ops["porte"].isna().sum())
    print(ops.groupby("origem", observed=True)["valor_contratado"].agg(["size", "sum"]))

    ops.to_parquet(TRATADOS / "operacoes.parquet", index=False)
    na.to_parquet(TRATADOS / "nao_automaticas.parquet", index=False)
    print(f"\nGravado em {TRATADOS}/ ({(TRATADOS / 'operacoes.parquet').stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
