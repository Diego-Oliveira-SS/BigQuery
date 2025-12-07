
from google.cloud import bigquery

def gcs_to_bq_billing(event):
    project_id = "telco-metrics-473116"
    dataset_id = "telco_metrics_curated"
    table_id = "billing"

    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    client = bigquery.Client(project=project_id)

    data = event.data               # capture event data dictionary
    bucket = data["bucket"]         # ex.: telco-metrics-raw
    name = data["name"]             # ex.: gross/gross_2025-10-08.csv
    uri = f"gs://{bucket}/{name}"   # ex.: gs://telco-metrics-raw/gross/gross_2025-10-08.csv
    
    print(f"Processing file: {uri}")
    
    # Configure the load job
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # Assuming the first row is a header
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,  # Append to existing table
        autodetect=False,  # Use existing destination table schema when appending
        ignore_unknown_values=True,
    )

    before_rows = client.get_table(table_ref).num_rows

    load_job = client.load_table_from_uri(
        uri,
        table_ref,
        job_config=job_config,
    )  

    load_job.result()  # Waits for the job to complete.
    after_rows = client.get_table(table_ref).num_rows
    loaded_rows = max(0, after_rows - before_rows)
    print(f"Loaded {loaded_rows} rows into {table_ref}. Total rows now {after_rows}.")