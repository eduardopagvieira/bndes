"""
Análise das operações de financiamento do BNDES, de 2002 a agosto de 2026.

Lê dados/tratados/operacoes.parquet (gerado por limpar.py) e produz

    resultados/*.csv   tabelas da análise (pequenas, ficam no repositório)
    figuras/*.png      gráficos usados no README

Todos os valores são o valor contratado, corrigido pelo IPCA para reais de setembro de 2026.
O ano de 2026 vai só até agosto.

Uso
    python analisar.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

TRATADOS = Path("dados/tratados")
AUX = Path("dados/auxiliares")
RESULTADOS = Path("resultados")
FIGURAS = Path("figuras")
BI = 1e9

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
APAGADO = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
AZUL, LARANJA, VERDE, AMARELO, CINZA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#b9b7ae"

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"],
    "font.size": 10,
    "figure.facecolor": SUPERFICIE,
    "axes.facecolor": SUPERFICIE,
    "savefig.facecolor": SUPERFICIE,
    "axes.edgecolor": EIXO,
    "axes.labelcolor": TINTA_2,
    "xtick.color": APAGADO,
    "ytick.color": APAGADO,
    "text.color": TINTA,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlelocation": "left",
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlepad": 30,
})
FONTE = ("Fonte: BNDES, dados abertos de operações de financiamento. IPCA do Banco Central. "
         "Valores em reais de setembro de 2026. Elaboração própria.")

# custo financeiro agrupado. TJ462, TJ453 e TJ6 são variações da TJLP usadas em programas específicos
CUSTOS = {"TJLP": "TJLP", "TJ462": "TJLP", "TJ453": "TJLP", "TJ6": "TJLP", "TLP": "TLP",
          "TAXA FIXA": "Taxa fixa", "TAXA FIXA EM US$": "Taxa fixa", "SELIC": "Selic",
          "75% da SELIC": "Selic", "90% da SELIC": "Selic"}
ORDEM_CUSTOS = ["TJLP", "TLP", "Taxa fixa", "Selic", "Outros"]
CORES_CUSTOS = [AZUL, LARANJA, VERDE, AMARELO, CINZA]
ORDEM_PORTES = ["Micro", "Pequena", "Média", "Grande"]
ORDEM_SETORES = ["Infraestrutura", "Indústria", "Comércio e serviços", "Agropecuária"]
PERIODOS = [(2002, 2008, "2002 a 2008"), (2009, 2015, "2009 a 2015"), (2016, 2021, "2016 a 2021"),
            (2022, 2026, "2022 a 2026")]


def bi(v, casas=0):
    return f"R$ {v / BI:,.{casas}f} bi".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, casas=0):
    return f"{v * 100:.{casas}f}%".replace(".", ",")


def inteiro(v):
    return f"{v:,.0f}".replace(",", ".")


def finalizar(fig, ax, titulo, sub, arquivo):
    tem_legenda = ax.get_legend() is not None          # a legenda fica entre o subtítulo e o gráfico
    ax.set_title(titulo, pad=50 if tem_legenda else 30)
    ax.annotate(sub, (0, 1), xycoords="axes fraction", xytext=(0, 30 if tem_legenda else 8), textcoords="offset points",
                color=TINTA_2, fontsize=9.5, va="bottom")
    fig.text(0.01, 0.01, FONTE, color=APAGADO, fontsize=8, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURAS / arquivo, dpi=160)
    plt.close(fig)


def eixo_bi(ax, eixo="y"):
    fmt = mticker.FuncFormatter(lambda v, _: f"{v / BI:,.0f}".replace(",", "."))
    (ax.yaxis if eixo == "y" else ax.xaxis).set_major_formatter(fmt)


def legenda(ax, itens, y=1.0):
    """Legenda numa linha, acima do gráfico e abaixo do subtítulo."""
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=n) for n, c in itens], loc="lower left", bbox_to_anchor=(0, y),
              ncol=len(itens), frameon=False, fontsize=9, handlelength=1, handleheight=1, borderaxespad=0.3)


# ---------------------------------------------------------------- análises

def serie_anual(d):
    t = d.pivot_table(index="ano", columns="origem", values="valor_contratado_real", aggfunc="sum",
                      observed=True).fillna(0)
    t.columns = ["indireta_automatica", "nao_automatica"]
    t["total"] = t.sum(axis=1)
    t["psi"] = d[d["psi"]].groupby("ano")["valor_contratado_real"].sum()
    t["psi"] = t["psi"].fillna(0)
    t["operacoes"] = d.groupby("ano").size()
    t.to_csv(RESULTADOS / "serie_anual.csv", float_format="%.0f")

    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = t.index.to_numpy()
    ax.bar(x, t["nao_automatica"], width=0.72, color=AZUL, edgecolor=SUPERFICIE, linewidth=1)
    ax.bar(x, t["indireta_automatica"], bottom=t["nao_automatica"], width=0.72, color=LARANJA,
           edgecolor=SUPERFICIE, linewidth=1)
    pico = t["total"].idxmax()
    for ano in (pico, 2019, 2024):
        ax.text(ano, t.loc[ano, "total"] + t["total"].max() * 0.015, bi(t.loc[ano, "total"]), ha="center",
                fontsize=8.5, color=TINTA_2)
    ax.text(2026, t.loc[2026, "total"] + t["total"].max() * 0.015, "até ago.", ha="center", fontsize=8.5,
            color=TINTA_2)
    eixo_bi(ax)
    ax.set_ylabel("R$ bilhões")
    ax.set_xticks(x[::2])
    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    legenda(ax, [("Operações não automáticas (diretas e grandes indiretas)", AZUL),
                 ("Operações indiretas automáticas (via bancos)", LARANJA)])
    finalizar(fig, ax, "Valor contratado com o BNDES por ano",
              "Em reais de setembro de 2026", "01_serie_anual.png")
    return t


def psi(d, serie):
    auto = d[d["origem"] == "Indireta automática"]
    t = auto.groupby(["ano", "psi"])["valor_contratado_real"].sum().unstack(fill_value=0)
    t.columns = ["outras", "psi"]
    t = t.loc[2007:2017]
    instrumentos = (d[d["psi"]].groupby("instrumento", observed=True)["valor_contratado_real"].sum()
                    .sort_values(ascending=False))
    instrumentos = instrumentos[instrumentos > 0]
    instrumentos.to_csv(RESULTADOS / "psi_instrumentos.csv", float_format="%.0f")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = t.index.to_numpy()
    ax.bar(x, t["psi"], width=0.72, color=AZUL, edgecolor=SUPERFICIE, linewidth=1)
    ax.bar(x, t["outras"], bottom=t["psi"], width=0.72, color=CINZA, edgecolor=SUPERFICIE, linewidth=1)
    for ano in x:
        tot = t.loc[ano].sum()
        if t.loc[ano, "psi"] > 0:
            ax.text(ano, tot + t.sum(axis=1).max() * 0.015, pct(t.loc[ano, "psi"] / tot), ha="center",
                    fontsize=8.5, color=TINTA_2)
    eixo_bi(ax)
    ax.set_ylabel("R$ bilhões")
    ax.set_xticks(x)
    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    legenda(ax, [("PSI", AZUL), ("Outras linhas", CINZA)])
    total_psi = serie["psi"].sum()
    finalizar(fig, ax, "O PSI dominou o crédito automático de 2009 a 2015",
              f"Operações indiretas automáticas por ano. O PSI somou {bi(total_psi)}, "
              "a maior parte em caminhões, ônibus e máquinas", "02_psi.png")
    return total_psi, instrumentos


def custo_financeiro(d):
    grupo = d["custo_financeiro"].astype(str).map(CUSTOS).fillna("Outros")
    t = d.groupby(["ano", grupo])["valor_contratado_real"].sum().unstack(fill_value=0)[ORDEM_CUSTOS]
    t = t.div(t.sum(axis=1), axis=0)
    t.to_csv(RESULTADOS / "custo_financeiro_ano.csv", float_format="%.4f")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.stackplot(t.index, t.T.to_numpy(), colors=CORES_CUSTOS, edgecolor=SUPERFICIE, linewidth=1.5)
    ax.axvline(2018, color=TINTA_2, linewidth=1, linestyle=(0, (3, 3)))
    ax.text(2018.25, 0.45, "Em 2018 a TLP\nsubstitui a TJLP\nnos novos contratos", va="center", fontsize=9,
            color=SUPERFICIE)
    ax.set_xlim(t.index.min(), t.index.max())
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: pct(v)))
    ax.set_xticks(range(2002, 2027, 2))
    ax.tick_params(length=0)
    legenda(ax, list(zip(ORDEM_CUSTOS, CORES_CUSTOS)))
    finalizar(fig, ax, "Da TJLP à TLP",
              "Parcela do valor contratado em cada ano, pelo custo financeiro do contrato. "
              "A TJLP era fixada pelo governo, a TLP segue os juros de mercado", "03_custo_financeiro.png")
    return t


def porte(d):
    t = pd.DataFrame({"operacoes": d.groupby("porte", observed=True).size(),
                      "valor": d.groupby("porte", observed=True)["valor_contratado_real"].sum()}).loc[ORDEM_PORTES]
    t["parcela_operacoes"] = t["operacoes"] / t["operacoes"].sum()
    t["parcela_valor"] = t["valor"] / t["valor"].sum()
    t["valor_medio"] = t["valor"] / t["operacoes"]
    t.to_csv(RESULTADOS / "porte.csv", float_format="%.4f")
    per = d.assign(periodo=periodo(d)).pivot_table(index="periodo", columns="porte", values="valor_contratado_real",
                                                    aggfunc="sum", observed=True)[ORDEM_PORTES]
    per = per.div(per.sum(axis=1), axis=0)
    per.to_csv(RESULTADOS / "porte_periodo.csv", float_format="%.4f")

    fig, ax = plt.subplots(figsize=(9, 3.9))
    y = np.arange(len(t))[::-1]
    h = 0.36
    ax.barh(y + h / 2, t["parcela_operacoes"], height=h, color=AZUL, edgecolor=SUPERFICIE, linewidth=1)
    ax.barh(y - h / 2, t["parcela_valor"], height=h, color=LARANJA, edgecolor=SUPERFICIE, linewidth=1)
    for yi, (_, linha) in zip(y, t.iterrows()):
        ax.text(linha["parcela_operacoes"] + 0.01, yi + h / 2, pct(linha["parcela_operacoes"]), va="center",
                fontsize=9, color=TINTA_2)
        ax.text(linha["parcela_valor"] + 0.01, yi - h / 2, pct(linha["parcela_valor"]), va="center",
                fontsize=9, color=TINTA_2)
    ax.set_yticks(y, t.index, color=TINTA)
    ax.set_xlim(0, 0.9)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: pct(v)))
    ax.grid(axis="x", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.spines["left"].set_visible(False)
    legenda(ax, [("Parcela das operações", AZUL), ("Parcela do valor", LARANJA)])
    finalizar(fig, ax, "Muitas operações pequenas, pouco dinheiro",
              "Porte do cliente na data do contrato, 2002 a 2026", "04_porte.png")
    return t, per


def periodo(d):
    rotulos = pd.Series(index=d.index, dtype=object)
    for ini, fim, nome in PERIODOS:
        rotulos[(d["ano"] >= ini) & (d["ano"] <= fim)] = nome
    return pd.Categorical(rotulos, [p[2] for p in PERIODOS], ordered=True)


def setores(d):
    t = d.assign(periodo=periodo(d)).pivot_table(index="periodo", columns="setor", values="valor_contratado_real",
                                                  aggfunc="sum", observed=True)[ORDEM_SETORES]
    anos = np.array([fim - ini + 1 for ini, fim, _ in PERIODOS], dtype=float)
    anos[-1] = 4 + 8 / 12                                  # 2026 vai até agosto
    media_anual = t.div(anos, axis=0)
    parcela = t.div(t.sum(axis=1), axis=0)
    parcela.to_csv(RESULTADOS / "setor_periodo.csv", float_format="%.4f")
    media_anual.to_csv(RESULTADOS / "setor_media_anual.csv", float_format="%.0f")
    sub = (d.groupby("subsetor", observed=True)["valor_contratado_real"].sum().sort_values(ascending=False))
    sub.to_csv(RESULTADOS / "subsetores.csv", float_format="%.0f")

    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(len(media_anual))
    w = 0.2
    cores = [AZUL, LARANJA, VERDE, AMARELO]
    for i, (s, c) in enumerate(zip(ORDEM_SETORES, cores)):
        v = media_anual[s].to_numpy()
        ax.bar(x + (i - 1.5) * w, v, width=w, color=c, edgecolor=SUPERFICIE, linewidth=1)
        for xi, vi in zip(x, v):
            ax.text(xi + (i - 1.5) * w, vi + media_anual.max().max() * 0.015, f"{vi / BI:.0f}", ha="center",
                    fontsize=8, color=TINTA_2)
    eixo_bi(ax)
    ax.set_ylabel("R$ bilhões por ano")
    ax.set_xticks(x, media_anual.index, color=TINTA)
    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    legenda(ax, list(zip(ORDEM_SETORES, cores)))
    finalizar(fig, ax, "Infraestrutura é o principal destino em todos os períodos",
              "Média anual do valor contratado por setor. 2026 vai até agosto", "05_setores.png")
    return parcela, media_anual


def ufs(d):
    pop = pd.read_csv(AUX / "populacao_uf.csv").set_index("uf")["populacao"]
    recente = d[d["ano"] >= 2017]
    t = recente.groupby("uf", observed=True)["valor_contratado_real"].sum().to_frame("valor")
    t["populacao"] = pop
    t["por_habitante"] = t["valor"] / t["populacao"] / (9 + 8 / 12)     # média anual, 2017 a agosto de 2026
    t["regiao"] = recente.groupby("uf", observed=True)["regiao"].first()
    sem_uf = recente.loc[recente["uf"].isna(), "valor_contratado_real"].sum() / recente["valor_contratado_real"].sum()
    t = t.sort_values("por_habitante", ascending=False)
    t.to_csv(RESULTADOS / "uf.csv", float_format="%.2f")
    regioes = recente.groupby("regiao", observed=True)["valor_contratado_real"].sum().to_frame("valor")
    regioes["populacao"] = t.groupby("regiao", observed=True)["populacao"].sum()
    regioes["por_habitante"] = regioes["valor"] / regioes["populacao"] / (9 + 8 / 12)
    regioes.to_csv(RESULTADOS / "regiao.csv", float_format="%.2f")

    s = t["por_habitante"].sort_values()
    cores = {"Sul": AZUL, "Centro-Oeste": LARANJA, "Sudeste": VERDE, "Norte": AMARELO, "Nordeste": "#e87ba4"}
    fig, ax = plt.subplots(figsize=(9, 8))
    y = np.arange(len(s))
    ax.barh(y, s.to_numpy(), height=0.66, color=[cores[t.loc[u, "regiao"]] for u in s.index],
            edgecolor=SUPERFICIE, linewidth=1)
    for i, (u, v) in enumerate(s.items()):
        ax.text(v + s.max() * 0.01, i, f"R$ {inteiro(v)}", va="center", fontsize=8.5, color=TINTA_2)
    ax.set_yticks(y, s.index, color=TINTA)
    ax.set_xlim(0, s.max() * 1.15)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: inteiro(v)))
    ax.grid(axis="x", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.spines["left"].set_visible(False)
    legenda(ax, list(cores.items()))
    finalizar(fig, ax, "Crédito do BNDES por habitante",
              "Média anual de 2017 a agosto de 2026, em reais por habitante (população do Censo 2022)",
              "06_uf_por_habitante.png")
    return t, regioes, sem_uf


def clientes(d):
    c = d.groupby("cliente", observed=True)["valor_contratado_real"].agg(["sum", "size"])
    c = c.sort_values("sum", ascending=False)
    c.columns = ["valor", "operacoes"]
    c["parcela"] = c["valor"] / c["valor"].sum()
    c.head(100).to_csv(RESULTADOS / "maiores_clientes.csv", float_format="%.4f")
    top = c.head(15)["valor"].sort_values()

    fig, ax = plt.subplots(figsize=(9, 6.4))
    y = np.arange(len(top))
    ax.barh(y, top.to_numpy(), height=0.62, color=AZUL, edgecolor=SUPERFICIE, linewidth=1)
    for i, v in enumerate(top):
        ax.text(v + top.max() * 0.01, i, bi(v), va="center", fontsize=9, color=TINTA_2)
    nomes = [nome_curto(n) for n in top.index]
    ax.set_yticks(y, nomes, color=TINTA)
    ax.set_xlim(0, top.max() * 1.18)
    eixo_bi(ax, "x")
    ax.grid(axis="x", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.spines["left"].set_visible(False)
    finalizar(fig, ax, "Os 15 maiores clientes do BNDES",
              f"Valor contratado de 2002 a 2026. Os 100 maiores ficaram com {pct(c.head(100)['parcela'].sum())} "
              f"do total, entre {inteiro(len(c))} clientes", "07_maiores_clientes.png")
    return c


NOMES = {"PETROLEO BRASILEIRO S A PETROBRAS": "Petrobras", "NORTE ENERGIA S/A": "Norte Energia (Belo Monte)",
         "ESTADO DE SAO PAULO": "Estado de São Paulo", "VALE S.A.": "Vale", "BANCO DO BRASIL SA": "Banco do Brasil",
         "TRANSPORTADORA ASSOCIADA DE GAS S.A. - TAG": "TAG (gasodutos)", "SUZANO S.A.": "Suzano",
         "CAIXA ECONOMICA FEDERAL": "Caixa", "OI MOVEL S.A. - EM RECUPERACAO JUDICIAL": "Oi Móvel",
         "TELEFONICA BRASIL S.A.": "Telefônica (Vivo)", "TIM CELULAR S.A.": "TIM", "KLABIN S.A.": "Klabin",
         "JIRAU ENERGIA S.A.": "Jirau Energia", "SANTO ANTONIO ENERGIA S.A.": "Santo Antônio Energia",
         "BANCO REGIONAL DE DESENVOLVIMENTO DO EXTREMO SUL": "BRDE"}


def nome_curto(n):
    return NOMES.get(n, n.title()[:40])


def main():
    RESULTADOS.mkdir(exist_ok=True)
    FIGURAS.mkdir(exist_ok=True)
    d = pd.read_parquet(TRATADOS / "operacoes.parquet")
    print(f"{len(d):,} operações, {bi(d['valor_contratado_real'].sum())} em reais de set/2026")

    s = serie_anual(d)
    pico = s["total"].idxmax()
    boom = s.loc[2009:2014, "total"].mean()
    baixa = s.loc[2016:2023, "total"].mean()
    print(f"\nPico em {pico} com {bi(s.loc[pico, 'total'])}. Média 2009-2014 {bi(boom)}, 2016-2023 {bi(baixa)} "
          f"({pct(baixa / boom - 1)}). 2024 {bi(s.loc[2024, 'total'])}, 2025 {bi(s.loc[2025, 'total'])}")

    total_psi, inst = psi(d, s)
    auto = s.loc[2009:2015, "indireta_automatica"].sum()
    print(f"PSI {bi(total_psi)}, {pct(total_psi / auto)} das automáticas de 2009 a 2015")
    print(inst.head(5).div(BI).round(0).to_string())

    c = custo_financeiro(d)
    print("\nTJLP 2017", pct(c.loc[2017, "TJLP"]), "| TLP 2019", pct(c.loc[2019, "TLP"]),
          "| taxa fixa 2010", pct(c.loc[2010, "Taxa fixa"]))

    p, per = porte(d)
    print("\n", p[["parcela_operacoes", "parcela_valor", "valor_medio"]].round(3).to_string())
    print(per.round(3).to_string())

    parcela, media = setores(d)
    print("\n", parcela.round(3).to_string())

    u, r, sem_uf = ufs(d)
    print("\n", u[["por_habitante", "regiao"]].round(0).head(6).to_string())
    print(u[["por_habitante"]].round(0).tail(4).to_string())
    print(r.round(0).to_string(), f"\nsem UF (interestadual ou exterior) {pct(sem_uf, 1)}")

    cl = clientes(d)
    print(f"\nTop 10 {pct(cl.head(10)['parcela'].sum())}, top 100 {pct(cl.head(100)['parcela'].sum())}, "
          f"{inteiro(len(cl))} clientes")


if __name__ == "__main__":
    main()
