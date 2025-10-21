import pandas as pd
import io, csv
from google.cloud import storage
from google.cloud import bigquery
from datetime import date
from dateutil.relativedelta import relativedelta

PROJECT_ID   = "telco-metrics-473116"
BUCKET_NAME = "telco-metrics-raw"
DATASET_ID   = "telco_metrics_curated"
CUSTOMERS_TB = "customers"
BILLING_TB   = "billing"


TODAY = date.today()
csv_name = f"billing_{TODAY}.csv"
TODAY_DAY = TODAY.day
ciclo_venc = [(1,8), (8,15), (15,21), (21, 28), (25,11)]

month_cycle = []
vencimentos = []
for ciclo in ciclo_venc:
    month_cycle.append(ciclo[0])
    vencimentos.append(ciclo[1])


# Função para gerar a fatura do mês atual (se aplicável)
def fatura_atual(dt, dia_venc):
    if TODAY_DAY < dia_venc:
        current_venc = date(TODAY.year, TODAY.month, dia_venc)
    else:
        M_1 = TODAY + relativedelta(months=1)
        current_venc = date(M_1.year, M_1.month, dia_venc)
    return current_venc


if TODAY_DAY in month_cycle:
    

    bq = bigquery.Client(project=PROJECT_ID)
    sql = f"""
    SELECT ID_CLIENTE, DT_ENTRADA, VENCIMENTO, VALOR_PLANO, DESCONTO
    FROM `{PROJECT_ID}.{DATASET_ID}.{CUSTOMERS_TB}`
    where ciclo_faturamento = {TODAY_DAY} and status = 'A'   
    """
    clientes = bq.query(sql).to_dataframe()
else:
    clientes = pd.DataFrame()  # DataFrame vazio
    print("Nenhuma fatura a ser gerada hoje.")
    print("Dia do ciclo de faturamento não corresponde ao dia atual.")
    print("Programa Encerrado.")
    exit()

# Gera faturas (billing)
billing = []
for _, row in clientes.iterrows():
    id_cliente = row['ID_CLIENTE']

    if ciclo == 25:
        Vencimento = date(TODAY.year, TODAY.month, row['VENCIMENTO']) + relativedelta(months=1)
    else:
        Vencimento = date(TODAY.year, TODAY.month, row['VENCIMENTO'])

    
    ano = Vencimento.year
    mes = Vencimento.month
    id_fatura = f"F{id_cliente}{ano}{mes:02d}"
    dt_emissao = TODAY
    dt_vencimento = Vencimento
    valor_plano = row["VALOR_PLANO"]
    desconto = row["DESCONTO"]
    valor_base = (valor_plano - desconto)

    billing.append((
        id_fatura,
        id_cliente,
        dt_emissao,
        dt_vencimento,
        valor_plano,
        desconto,
        valor_base,
        ano,
        mes,
        TODAY,           # DT_INGESTAO
        "Billing_Cycle"  # FONTE
    ))


# Gera CSV em memória
output = io.StringIO()
w = csv.writer(output)
w.writerow([
   "ID_FATURA","ID_CLIENTE","DT_EMISSAO","DT_VENCIMENTO",
    "VALOR_PLANO","DESCONTO","VALOR_BASE","ANO","MES",
    "DT_INGESTAO","FONTE"
])  
for registro in billing:
    w.writerow(registro)

csv_string = output.getvalue()
output.close()

# Upload para GCS
gcs = storage.Client(project=PROJECT_ID)
bucket = gcs.bucket(BUCKET_NAME)
blob = bucket.blob(f"billing/{csv_name}")
blob.upload_from_string(csv_string, content_type="text/csv")
print(f"Arquivo {csv_name} enviado para {BUCKET_NAME}/billing/")





