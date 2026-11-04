# Financiamentos do BNDES

Projeto em andamento. Etapa atual é a coleta de dados.

## Pergunta

Para onde vai o crédito do BNDES? Como os financiamentos se distribuem por setor, porte da empresa e estado, e como isso mudou ao longo do tempo?

## Fonte

Portal de dados abertos do BNDES, conjunto Operações de financiamento (`https://dadosabertos.bndes.gov.br/dataset/operacoes-financiamento`).

São dois arquivos.

| Arquivo | Tamanho | Conteúdo |
|---|---|---|
| Operações indiretas automáticas | cerca de 1 GB | Operações feitas por bancos repassadores |
| Operações não automáticas | cerca de 20 MB | Operações diretas e indiretas avaliadas pelo BNDES, com descrição do projeto |

Os dois vêm com dicionário de dados em PDF. Os CSVs usam separador `;` e codificação latin1.

## Método

1. O script consulta a API CKAN do portal para descobrir os arquivos do conjunto, sem depender de links fixos que mudam a cada atualização.
2. Baixa os CSVs e os dicionários para `dados/brutos/`, que nunca são editados.

Próximas etapas são limpeza, séries históricas por setor, porte e UF e visualizações.

## Como rodar

```bash
pip install -r requirements.txt
python baixar_bndes.py --listar   # só mostra o que existe no portal
python baixar_bndes.py            # baixa tudo (cerca de 1,1 GB)
```

No Windows com Miniconda, use `rodar_bndes.bat`.

Para ler o arquivo grande no pandas, carregue só as colunas necessárias.

```python
pd.read_csv(caminho, sep=";", encoding="latin1", usecols=[...])
```

Os dados não ficam no repositório. O script recria tudo a partir do portal.
