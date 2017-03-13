from __future__ import unicode_literals

import hashlib

import boto.glacier
from moto.core import BaseBackend, BaseModel

from .utils import get_job_id


class ArchiveJob(BaseModel):

    def __init__(self, job_id, archive_id):
        self.job_id = job_id
        self.archive_id = archive_id

    def to_dict(self):
        return {
            "Action": "InventoryRetrieval",
            "ArchiveId": self.archive_id,
            "ArchiveSizeInBytes": 0,
            "ArchiveSHA256TreeHash": None,
            "Completed": True,
            "CompletionDate": "2013-03-20T17:03:43.221Z",
            "CreationDate": "2013-03-20T17:03:43.221Z",
            "InventorySizeInBytes": "0",
            "JobDescription": None,
            "JobId": self.job_id,
            "RetrievalByteRange": None,
            "SHA256TreeHash": None,
            "SNSTopic": None,
            "StatusCode": "Succeeded",
            "StatusMessage": None,
            "VaultARN": None,
        }


class Vault(BaseModel):

    def __init__(self, vault_name, region):
        self.vault_name = vault_name
        self.region = region
        self.archives = {}
        self.jobs = {}

    @property
    def arn(self):
        return "arn:aws:glacier:{0}:012345678901:vaults/{1}".format(self.region, self.vault_name)

    def to_dict(self):
        return {
            "CreationDate": "2013-03-20T17:03:43.221Z",
            "LastInventoryDate": "2013-03-20T17:03:43.221Z",
            "NumberOfArchives": None,
            "SizeInBytes": None,
            "VaultARN": self.arn,
            "VaultName": self.vault_name,
        }

    def create_archive(self, body):
        archive_id = hashlib.sha256(body).hexdigest()
        self.archives[archive_id] = body
        return archive_id

    def get_archive_body(self, archive_id):
        return self.archives[archive_id]

    def delete_archive(self, archive_id):
        return self.archives.pop(archive_id)

    def initiate_job(self, archive_id):
        job_id = get_job_id()
        job = ArchiveJob(job_id, archive_id)
        self.jobs[job_id] = job
        return job_id

    def list_jobs(self):
        return self.jobs.values()

    def describe_job(self, job_id):
        return self.jobs.get(job_id)

    def get_job_output(self, job_id):
        job = self.describe_job(job_id)
        archive_body = self.get_archive_body(job.archive_id)
        return archive_body


class GlacierBackend(BaseBackend):

    def __init__(self, region_name):
        self.vaults = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def get_vault(self, vault_name):
        return self.vaults[vault_name]

    def create_vault(self, vault_name):
        self.vaults[vault_name] = Vault(vault_name, self.region_name)

    def list_vaules(self):
        return self.vaults.values()

    def delete_vault(self, vault_name):
        self.vaults.pop(vault_name)

    def initiate_job(self, vault_name, archive_id):
        vault = self.get_vault(vault_name)
        job_id = vault.initiate_job(archive_id)
        return job_id

    def list_jobs(self, vault_name):
        vault = self.get_vault(vault_name)
        return vault.list_jobs()


glacier_backends = {}
for region in boto.glacier.regions():
    glacier_backends[region.name] = GlacierBackend(region)
