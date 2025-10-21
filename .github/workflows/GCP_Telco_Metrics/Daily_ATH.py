import csv, io, random, uuid, pandas as pd
from google.cloud import bigquery, storage
from datetime import date, datetime


# Script para popular tabela ATH (interações) 
# Gera csv diário no bucket: ath_YYYYMMDD.csv

PROJECT_ID   = "telco-metrics-473116"
BUCKET_NAME = "telco-metrics-raw"
DATASET_ID   = "telco_metrics_curated"
CUSTOMERS_TB = "customers"
ATH_TB       = "ath"

# Captura de clientes ativos
bq = bigquery.Client(project=PROJECT_ID)
sql = f"""
SELECT ID_CLIENTE, DT_ENTRADA
FROM `{PROJECT_ID}.{DATASET_ID}.{CUSTOMERS_TB}`
WHERE STATUS = 'A'  # Apenas clientes ativos    
"""
clientes = bq.query(sql).to_dataframe()


# 2) motivos (informação, solicitação, reclamação)

motivos_info = [
    ("informacao", "planos", "detalhes_fatura"),
    ("informacao", "tecnico", "agendamento"),
    ("informacao", "cadastro", "dados_pessoais"),]
motivos_soli = [
    ("solicitacao", "segunda_via", "boleto"),
    ("solicitacao", "mudanca_plano", "upgrade"),
    ("solicitacao", "visita_tecnica", "reparo"),]
motivos_recl = [
    ("reclamacao", "cobranca", "valor_divergente"),
    ("reclamacao", "qualidade", "internet_lenta"),
    ("reclamacao", "atendimento", "tempo_espera"),]
catalogo = {
    "informacao": motivos_info,
    "solicitacao": motivos_soli,
    "reclamacao": motivos_recl,
}
# =========================
# 3) Geração aleatória por cliente
#    - volume de interações por cliente: 0..6
#    - cada cliente tem "taxa de reclamação" própria (aleatória)
#    - retenção = 10% (True)
# =========================
def sorteia_tipo(p_reclamacao: float):
    # pesos: ajusta reclamação por cliente, restante divide entre informação/solicitação        
    p_rec = max(0.0, min(1.0, p_reclamacao))
    restante = 1.0 - p_rec
    p_info = restante * 0.6
    
    p_soli = restante * 0.4
    return random.choices(
        ["informacao", "solicitacao", "reclamacao"],
        weights=[p_info, p_soli, p_rec],
        k=1
    )[0]

# Gera uma consulta das interações no dia de hoje, 
# captura clientes aleatórios 
# motivos aleatórios

registros = []
TODAY = date.today()

for _, c in clientes.iterrows():
    if random.random() < 0.02:  # 2% de chance de gerar interações para esse cliente
        id_cliente = c["ID_CLIENTE"]
        dt_entrada = c["DT_ENTRADA"]
        inicio_janela = TODAY
        fim_janela = TODAY

        # probabilidade de reclamação exclusiva desse cliente (0%..60%)
        p_reclamacao = random.random() * 0.60
        
        tipo = sorteia_tipo(p_reclamacao)
        m1, m2, m3 = random.choice(catalogo[tipo])

        dt_interacao = TODAY
        id_interacao = str(uuid.uuid4())
        aht_seg = random.randint(120, 1200)  # 2 min    a 20 min
        retencao = random.random() < 0.10  # 10% de chance de retenção
        registros.append([
            id_interacao,
            id_cliente,
            dt_interacao,
            m1,
            m2,
            m3,
            tipo,
            retencao,
            aht_seg,
            dt_interacao.year,  # ano
            dt_interacao.month, # mes
            datetime.now(),               # DT_INGESTAO
            "Daily_ATH"          # FONTE
        ])

# Gera CSV em memória
output = io.StringIO()
w = csv.writer(output)
w.writerow([
    "ID_INTERACAO", "ID_CLIENTE", "DT_INTERACAO", "MOTIVO1", "MOTIVO2", "MOTIVO3",
    "TIPO", "RETENCAO", "AHT_SEG", "ANO", "MES", "DT_INGESTAO", "FONTE"
])
for registro in registros:
    w.writerow(registro)

csv_string = output.getvalue()
output.close()

print(f"Arquivo carregado em memória com {len(registros)} registros. Inicializando upload...")

# Upload para o GCS
csv_name = f"ath_{TODAY}.csv"
gcs = storage.Client(project=PROJECT_ID)
bucket = gcs.bucket(BUCKET_NAME)
blob = bucket.blob(f"ath/{csv_name}")
blob.upload_from_string(csv_string, content_type="text/csv")

print(f"Arquivo {csv_name} enviado para {BUCKET_NAME}/ath/")