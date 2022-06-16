#!/usr/bin/env python

import sys
import json
import os
from azure.identity import AzureCliCredential
from azure.keyvault.secrets import SecretClient

from DatabricksApi.Jobs import DatabricksJobsAPI


def get_databricks_secrets_keyvault(keyvault_url, secretName):
    '''
    Get secrets from keyVault
    :param
        keyvault_url(str): The keyvault to use
        secretName(str): Name of secret to return
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
        dir: Updates the Json file with correct cluster Id
        cluster_id(str): Returns the cluster id to use
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


def update_schedule(dir, env):
    '''
    Updates the json file with PAUSED or UNPASUED depends on environment
    :param 
        dir: path to files
        env: environment to deploy to
    '''
    try:
        for filename in os.listdir(dir):
            if filename.endswith(".json"):
                file = (os.path.join(dir, filename))
                with open(file, 'r+') as f:
                    json_object = json.load(f)
                f.close()

                if('schedule' in json_object):
                    if env in ["sbox", "dev"]:
                        status = 'PAUSED'
                        json_object['schedule']['pause_status'] = status
                    else:
                        status = "UNPAUSED"
                        json_object['schedule']['pause_status'] = status

            # Save our changes to JSON file
            with open(file, 'w') as f:
                json.dump(json_object, f, indent=4)
            f.close()

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
            f.close()
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


def recursion_lower(x):
    '''
    Function to convert object and value in json_object to lower_case
    params x:

    '''
    if type(x) is str:
        return x.lower()
    elif type(x) is list:
        return [self.recursion_lower(i) for i in x]
    elif type(x) is dict:
        return {self.recursion_lower(k): self.recursion_lower(v) for k, v in x.items()}
    else:
        return x


def check_tags(dir, squadname):
    '''
    function to update tags object in file to lower_case
    :param dir:
        path to files
    '''
    for filename in os.listdir(dir):
        if filename.endswith(".json"):
            file = (os.path.join(dir, filename))
            with open(file, 'r+') as f:
                json_object = json.load(f)
            f.close()
            if 'tags' in json_object:
                if json_object['tags'] == squadname:
                    tags_lower = recursion_lower(json_object['tags'])
                    json_object['tags'] = tags_lower
                else:
                    raise AttributeError(
                        'Tag in job "%s" does not match the squad name.' % filename)
            else:
                raise ValueError(
                    'Job "%s" does not contain a tag.' % filename)

        with open(file, 'w') as f:
            json.dump(json_object, f, indent=4)


def main():

    squad_name = sys.argv[1].lower()
    kv_name = sys.argv[2]
    environment = sys.argv[3]

    cluster_id_name = 'atlas-databricks-maiacmn-%s-id' % squad_name
    keyvault_url = 'https://%s.vault.azure.net/' % kv_name
    local_job_folder = './artifact/Databricks-jobs/'

    # Check if local jobs are tagged with squad name. Raises error if tags are missing or do not match the squad name.
    check_tags(local_job_folder, squad_name)
    # Update schedule and pause schedules if environment is dev or test.
    update_schedule(local_job_folder, environment)
    # Update clusterId based on cluster_id retrieved from key vault.
    add_clusterId(local_job_folder, cluster_id)

    # Fetch jobs from repository
    local_jobs = get_local_jobs(local_job_folder)

    # Get keys from vault
    dbr_token = get_databricks_secrets_keyvault(
        keyvault_url, 'atlas-maiacmn-databricks-pat')
    dbr_url = get_databricks_secrets_keyvault(
        keyvault_url, 'atlas-maiacmn-databricks-url')
    cluster_id = get_databricks_secrets_keyvault(keyvault_url, cluster_id_name)

    databricks_jobs = DatabricksJobsAPI(dbr_url, dbr_token)

    # Get jobs from databricks workspace
    cluster_jobs = databricks_jobs.get_jobs()

    # Create and update jobs
    print('Local jobs used for updating:' + str(local_jobs))
    upsert_jobs(databricks_jobs, local_jobs, cluster_jobs)


if __name__ == "__main__":
    main()
