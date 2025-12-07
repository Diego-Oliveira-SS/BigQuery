import os
import sys
import base64
import json

from flask import Flask, request

# adiciona a pasta raiz do repo no PYTHONPATH
# para conseguir importar gross.py, billing.py etc.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from scripts.gross import gcs_to_bq_gross
from scripts.billing import gcs_to_bq_billing
from scripts.payments import gcs_to_bq_payments
from scripts.ath import gcs_to_bq_ath


class SimpleEvent:
    def __init__(self, bucket: str, name: str):
        # imita o event.data["bucket"] / ["name"] que você usa no Cloud Functions
        self.data = {
            "bucket": bucket,
            "name": name,
        }


app = Flask(__name__)


@app.post("/")
def start_workflow():

    envelope = request.get_json(silent=True) or {}
    message = envelope.get("message", {})

    data_b64 = message.get("data")
    if not data_b64:
        print("Mensagem sem campo 'data'. Ignorando.")
        return ("", 204)

    payload_str = base64.b64decode(data_b64).decode("utf-8")
    payload = json.loads(payload_str)

    # formato JSON_API_V1 vindo da notificação do bucket
    bucket = payload.get("bucket")
    name = payload.get("name")

    print(f"Recebido via Pub/Sub: bucket={bucket}, name={name}")

    if not bucket or not name:
        print("Payload sem bucket ou name. Ignorando.")
        return ("", 204)

    event = SimpleEvent(bucket=bucket, name=name)

    # MESMA lógica do seu Cloud Function atual
    if name.startswith("gross/gross"):
        gcs_to_bq_gross(event)
    elif name.startswith("billing/billing"):
        gcs_to_bq_billing(event)
    elif name.startswith("payments/payments"):
        gcs_to_bq_payments(event)
    elif name.startswith("ath/ath"):
        gcs_to_bq_ath(event)
    else:
        print(f"Nenhum handler para objeto: {name}")

    return ("", 204)


if __name__ == "__main__":
    # para rodar local se quiser testar
    app.run(host="0.0.0.0", port=8080)
