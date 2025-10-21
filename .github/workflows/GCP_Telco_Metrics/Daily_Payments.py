# Populate_Payments.py

import pandas as pd, csv, random, io
from google.cloud import bigquery, storage
from datetime import date

# Variáveis (Ajustar Conforme o Projeto)
PROJECT_ID    = "telco-metrics-473116"
BUCKET_NAME = "telco-metrics-raw"       # ex.: gs://telco-metrics-raw
DATASET_ID    = "telco_metrics_curated"
CUSTOMERS_TB  = "customers"
BILLING_TB    = "billing"
PAYMENTS_TB   = "payments"

# Políticas de pagamento
STATUS_PGTO = ["pago", "inadimplente"]
METODOS  = ["pix", "boleto", "cartao"]
PESOS_MP = [0.60, 0.25, 0.15]  # soma 1.0

today = date.today()

# Captura faturas (billing) ainda sem pagamento (evita duplicidade)
bq = bigquery.Client(project=PROJECT_ID)
sql_billing = f"""
    SELECT a.ID_FATURA, a.ID_CLIENTE, a.DT_VENCIMENTO, a.VALOR_BASE
    FROM `{PROJECT_ID}.{DATASET_ID}.{BILLING_TB}` a
        left join `{PROJECT_ID}.{DATASET_ID}.{PAYMENTS_TB}` b 
        on a.ID_FATURA = b.ID_FATURA
    where 
        b.ID_PAGAMENTO is null
        and a.DT_VENCIMENTO + interval 90 day >= current_date()
        """
billing = bq.query(sql_billing).to_dataframe()


# Gera pagamentos (payments)
pagamentos = []
for _, row in billing.iterrows():
        # Ajusta pesos para evitar muitos registros futuros
        # Faturas com vencimento futuro tem maior chance de pagamento em comparação a faturas vencidas
        if row["DT_VENCIMENTO"] >= today:
            STATUS_PESO = [0.35, 0.65]  # soma 1.0 - Meta 60% pago em 5 dias
        else:
            STATUS_PESO = [0.1, 0.9]  # soma 1.0 - Meta 95% pago em 90 dias

        if random.choices(STATUS_PGTO, weights=STATUS_PESO, k=1)[0] == "pago":
            id_cliente    = row["ID_CLIENTE"]
            id_fatura     = row["ID_FATURA"]
            vencimento    = row["DT_VENCIMENTO"]
            valor_devido  = row["VALOR_BASE"]
            ano_venc      = int(row["DT_VENCIMENTO"].year)
            mes_venc      = int(row["DT_VENCIMENTO"].month)
            valor_pago    = row["VALOR_BASE"]
            desconto      = valor_devido - valor_pago
            metodo        = random.choices(METODOS, weights=PESOS_MP, k=1)[0]
            dt_pagto      = today
            dias_atraso   = (vencimento - pd.Timestamp.utcnow().date()).days
            if dias_atraso > 0:
                status_pg = "pago"
            else:
                status_pg = "atrasado"
            id_pagamento  = f"P{ano_venc}{mes_venc:02d}-{id_cliente}"

            pagamentos.append({
                "ID_PAGAMENTO":     id_pagamento,
                "ID_FATURA":        id_fatura,
                "ID_CLIENTE":       id_cliente,
                "DT_PAGAMENTO":     pd.to_datetime(dt_pagto).date().isoformat(),
                "VALOR_FATURA":     valor_devido,
                "VALOR_PAGO":       valor_pago,
                "DESCONTO":         desconto,
                "METODO_PAGAMENTO": metodo,
                "STATUS_PAGAMENTO": status_pg,
                "DT_VENCIMENTO":    vencimento,
                "DIAS_ATRASO":      int(dias_atraso),
                "ANO":              int((dt_pagto).year),
                "MES":              int((dt_pagto).month),
                "DT_INGESTAO":      pd.Timestamp.utcnow().isoformat(),
                "FONTE":            "Daily_Payments"
            })

# Gera CSV em memória
output = io.StringIO()
w = csv.writer(output)
w.writerow([
    "ID_PAGAMENTO","ID_FATURA","ID_CLIENTE","DT_PAGAMENTO",
    "VALOR_FATURA","VALOR_PAGO","DESCONTO","METODO_PAGAMENTO",
    "STATUS_PAGAMENTO","DT_VENCIMENTO","DIAS_ATRASO",
    "ANO","MES","DT_INGESTAO","FONTE"
])  
columns = [
    "ID_PAGAMENTO","ID_FATURA","ID_CLIENTE","DT_PAGAMENTO",
    "VALOR_FATURA","VALOR_PAGO","DESCONTO","METODO_PAGAMENTO",
    "STATUS_PAGAMENTO","DT_VENCIMENTO","DIAS_ATRASO",
    "ANO","MES","DT_INGESTAO","FONTE"
]
for registro in pagamentos:
    w.writerow([registro[col] for col in columns])

csv_string = output.getvalue()
output.close()

# Nome do arquivo CSV
csv_name = f"payments_{today}.csv"

# Upload para GCS
gcs = storage.Client(project=PROJECT_ID)
bucket = gcs.bucket(BUCKET_NAME)
blob = bucket.blob(f"payments/{csv_name}")
blob.upload_from_string(csv_string, content_type="text/csv")

import logging

logging.basicConfig(level=logging.INFO)
logging.info(f"Arquivo {csv_name} enviado para {BUCKET_NAME}/payments/")





