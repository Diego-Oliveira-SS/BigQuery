
from google.cloud import bigquery, storage

def gcs_to_bq_gross(event):
    print("Starting GCS to BigQuery gross data load...")

    project_id = "telco-metrics-473116"
    dataset_id = "telco_metrics_raw"

    name = event.data["name"]                           # ex.: gross/gross_loja_2025-10-20.csv
    table_id = name.split("/")[-1][0:-15]               # gross_loja_2025-10-20.csv  --> gross_loja
    table_ref = f"{project_id}.{dataset_id}.{table_id}" # ex.: telco-metrics-473116.telco_metrics_raw.gross_loja

    client = bigquery.Client(project=project_id)

    data = event.data               # capture event data dictionary
    bucket = data["bucket"]         # ex.: telco-metrics-raw
    file_name = data["name"]        # ex.: gross/gross_2025-10-08.csv
    uri = f"gs://{bucket}/{file_name}"   # ex.: gs://telco-metrics-raw/gross/gross_loja_2025-10-08.csv
    
    print(f"Processing file: {uri}")
    
    # Get the existing table schema
    table = client.get_table(table_ref)
    schema = table.schema
    
    # Configure the load job
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # Assuming the first row is a header
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,  # Append to existing table
        schema=schema,  # Use existing table schema explicitly
        ignore_unknown_values=True,
    )
    
    print(f"Loading data into {table_ref}...")

    load_job = client.load_table_from_uri(
        uri,
        table_ref,
        job_config=job_config,
    )  

    load_job.result()  # Waits for the job to complete.
    
    print(f"Load job finished for {table_ref}.")
    

    # Move the processed file to the LOADED folder

    storage_client = storage.Client(project=project_id)
    folder = name.split("/")[0]               # ex.: gross
    destination_blob_name = f"{folder}/LOADED/{file_name.split('/')[-1]}"
    bucket_obj = storage_client.bucket(bucket)
    blob = bucket_obj.blob(file_name)
    bucket_obj.copy_blob(blob, bucket_obj, destination_blob_name)
    blob.delete()
    print(f"Moved file gs://{bucket}/{file_name} to gs://{bucket}/{destination_blob_name}")
