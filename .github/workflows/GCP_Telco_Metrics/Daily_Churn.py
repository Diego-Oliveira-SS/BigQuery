
# Script Python para simular churn diário
# Seleciona aleatoriamente clientes na base principal e marca como churn
# alimenta a base de clientes inativos (base_churn)

import random
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from google.cloud import bigquery
import pandas as pd, pandas_gbq

# Variáveis (ajustar conforme o projeto)
PROJECT_ID = "telco-metrics-473116"         # ex.: telco-metrics-473116
BUCKET_NAME = "telco-metrics-raw"       # ex.: gs://telco-metrics-raw
DATASET_ID = "telco_metrics_curated"
CLIENTES_TABLE = "customers"
CHURN_TABLE = "base_churn"
BATCH_SIZE = 60


TODAY = datetime.today().date()
YESTERDAY = TODAY - timedelta(days=1)
CHURN_SIZE = BATCH_SIZE + random.randint(-10, 30)  # Variação de +/- 10 clientes
bq = bigquery.Client(project=PROJECT_ID)

# Captura base de clientes ativos para simulação de churn  
sql_clientes = f"""
    SELECT ID_CLIENTE
    FROM `{PROJECT_ID}.{DATASET_ID}.{CLIENTES_TABLE}`
    WHERE Status = 'A'
    ORDER BY RAND()
    LIMIT {CHURN_SIZE}
"""
query_job = bq.query(sql_clientes)
base_churn = list(query_job.result())

# Insere ex-clientes na base de churn
if base_churn:
    ids_clientes = [cliente[0] for cliente in base_churn]
    rows_to_insert = [
        {
            "ID_CLIENTE": cliente_id,
            "DT_CHURN": YESTERDAY,
            "MOTIVO_CHURN": random.choice(["Preço", "Concorrência", "Insatisfação", "Mudança de Necessidade"]),
            "TIPO_CANCELAMENTO": random.choice(["Voluntário", "Involuntário"]),
            "FEEDBACK_CLIENTE": random.choice(["Serviço ruim", "Preço alto", "Mudança de plano", "Outro"]),
            "FONTE": "Daily_Churn"
        }
        for cliente_id in ids_clientes
    ]

# Inclui na tabela de churn
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{CHURN_TABLE}"
    
    pandas_gbq.to_gbq(
        pd.DataFrame(rows_to_insert),
        table_id,
        project_id=PROJECT_ID,
        if_exists='append'
    )

print(f"{len(rows_to_insert)} clientes inseridos na base de churn.")


# Atualiza STATUS na tabela de clientes para 'I' (inativo)
if base_churn:
    ids_clientes = [cliente[0] for cliente in base_churn]
    ids_clientes_str = ', '.join([f"'{id}'" for id in ids_clientes])
    sql_update = f"""
        UPDATE `{PROJECT_ID}.{DATASET_ID}.{CLIENTES_TABLE}`
        SET STATUS = 'I'
        WHERE ID_CLIENTE IN ({ids_clientes_str})
    """
    query_job = bq.query(sql_update)
    query_job.result()  # Espera a conclusão
    print("Tabela de clientes atualizada com sucesso.")
else:
    print("Nenhum cliente atualizado.")

print("Processo de churn concluído.")
    