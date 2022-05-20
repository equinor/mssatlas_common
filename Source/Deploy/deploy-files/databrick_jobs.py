#!/usr/bin/env python

from pkgutil import get_data
import sys
import json
import os
from azure.identity import AzureCliCredential
from azure.keyvault.secrets import SecretClient
from click import echo
from requests import get

from DatabricksApi.Jobs import DatabricksJobsAPI
import time


def get_databricks_secrets_keyvault(keyvault_url, secretName):
    '''
    Get secrets from keyVault
    :param
        keyvault_url(str): The keyvault to use
        secretName(str): Secretname you wanna return
    '''
    try:
        credential = AzureCliCredential()
        client = SecretClient(vault_url=keyvault_url, credential=credential)
        secret = client.get_secret(secretName)
        return secret.value
    except Exception as e:
        print(e)


def add_clusterId(dir, cluster_id):
    '''
    :param
        dir: Updates the Json file with correct Cluster Id.
        cluster_id(str): Returns the clusterid to use
    '''
    try:
        for filename in os.listdir(dir):
            if filename.endswith(".json"):
                file = (os.path.join(dir, filename))
                with open(file, 'r+') as f:
                    json_object = json.load(f)
                f.close()

                if 'tasks' in json_object:
                    for i in json_object['tasks']:
                        for key in i:
                            if key == 'existing_cluster_id':
                                i[key] = cluster_id
                elif 'existing_cluster_id' in json_object:
                    json_object['existing_cluster_id'] = cluster_id
            # Save our changes to JSON file
            with open(file, 'w') as f:
                json.dump(json_object, f, indent=4)
            f.close()

    except Exception as e:
        print(e)


def update_schedule(dir, keyurl):
    '''
    Updates the json file with PAUSED or UNPASUED depends on environment
    :param 
        dir: path to files
        keyurl: Keyvault to use
    '''
    try:
        for filename in os.listdir(dir):
            if filename.endswith(".json"):
                file = (os.path.join(dir, filename))
                with open(file, 'r+') as f:
                    json_object = json.load(f)
                url = keyurl.split("-")
                if url[2] in ["sbox", "dev", "test"]:
                    status = 'PAUSED'
                    json_object['schedule']['pause_status'] = status
                else:
                    status = "UNPAUSED"
                    json_object['schedule']['pause_status'] = status
            # Save our changes to JSON file
            with open(file, 'w') as f:
                json.dump(json_object, f, indent=4)

    except Exception as e:
        print(e)


def get_local_jobs(folder):
    '''
    Return files from input folder
    :param 
        folder: string    
    '''
    try:
        local_jobs = []
        for file in [os.path.join(folder, filename) for filename in os.listdir(folder)]:
            with open(file, 'r') as f:
                local_jobs.append(json.loads(f.read()))
        return local_jobs
    except Exception as e:
        print(e)

# _TODO: Only update if theres any change


def upsert_jobs(databricks_jobs, local_jobs, cluster_jobs):
    cluster_job_names = [job['settings']['name'] for job in cluster_jobs]
    cluster_jobs_dict = databricks_jobs.get_jobs_dict()

    if local_jobs is None:
        print('No local jobs found')
        return
    for local_job in local_jobs:
        try:
            if local_job['name'] not in cluster_job_names:
                print(f"Creating job '{local_job['name']}'")
                databricks_jobs.create_job(local_job)
            else:
                cluster_job_id = cluster_jobs_dict[local_job['name']]
                print(f"Updating job '{local_job['name']}'")
                databricks_jobs.update_job(local_job, cluster_job_id)

        except Exception as e:
            continue


def main():

    cluster_id_name = 'atlas-databricks-maiacmn-%s-id' % sys.argv[1].lower()
    keyvault_url = 'https://%s.vault.azure.net/' % sys.argv[2]

    # Get keys from vault
    dbr_token = get_databricks_secrets_keyvault(
        keyvault_url, 'atlas-maiacmn-databricks-pat')
    dbr_url = get_databricks_secrets_keyvault(
        keyvault_url, 'atlas-maiacmn-databricks-url')
    cluster_id = get_databricks_secrets_keyvault(keyvault_url, cluster_id_name)

    databricks_jobs = DatabricksJobsAPI(dbr_url, dbr_token)

    # Update schedule and pause schedules if environment is dev or test.
    update_schedule('./artifact/Databricks-jobs/', keyvault_url)
    # Update clusterId based on cluster_id retrieved from key vault.
    add_clusterId('./artifact/Databricks-jobs/', cluster_id)

    # Fetch jobs from repository
    folder = './artifact/Databricks-jobs/'
    local_jobs = get_local_jobs(folder)

    # Get jobs from databricks workspace
    cluster_jobs = databricks_jobs.get_jobs()

    # Create and update jobs
    upsert_jobs(databricks_jobs, local_jobs, cluster_jobs)


if __name__ == "__main__":
    main()
