import requests


class DatabricksJobsAPI:
    def __init__(self, databricks_url, token):
        self.url = databricks_url
        self.headers = {'Authorization': 'Bearer %s' % token}

    def delete_job(self, job_id):
        response = requests.post(self.url + '/api/2.1/jobs/delete',
                                 headers=self.headers,
                                 data='{"job_id" :%s}' % job_id)
        return response.status_code

    def create_job(self, job):
        '''
        Function to create jobs on Cluster
        :params job
            Json job template
        '''
        response = requests.post(self.url + '/api/2.1/jobs/create',
                                 headers=self.headers,
                                 json=job)
        return response.status_code

    def get_jobs_dict(self):
        '''
        Function to create A dict where Jobname is the Key
        '''
        job_list = self.get_jobs()
        jobs_dict = {jobs['settings']['name']: jobs['job_id'] for jobs in job_list}
        return jobs_dict

    def get_jobs(self):
        '''
        Function to list the jobs from the Databricks API
        '''
        joblist = []
        response = requests.get(self.url + '/api/2.1/jobs/list', headers=self.headers)
        data = response.json()
        if data != {'has_more': False}:
            joblist = data['jobs']
        return joblist

    def get_a_job(self, job_id):
        '''
        Function to get a jobs as json object based on Job id
        :params job_id
            Job_id

        '''
        response = requests.get(self.url + f'/api/2.1/jobs/get?job_id={job_id}', headers=self.headers)
        return response.json()

    def change_job_activity(self, job_id, active: bool):
        job = self.get_a_job(job_id)
        job['settings']['schedule']['pause_status'] = 'UNPAUSED' if active else 'PAUSED'
        return self.update_job(job, job_id)

    def update_job(self, job, job_id):
        updated_job = {
            "job_id": int(job_id),
            "new_settings": job
        }
        response = requests.post(self.url + '/api/2.1/jobs/update',
                                 headers=self.headers,
                                 json=updated_job)
        return response.status_code

    
