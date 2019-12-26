from __future__ import unicode_literals

import hashlib

import datetime

from boto3 import Session

from moto.core import BaseBackend, BaseModel

from .utils import get_job_id


class Job(BaseModel):
    def __init__(self, tier):
        self.st = datetime.datetime.now()

        if tier.lower() == "expedited":
            self.et = self.st + datetime.timedelta(seconds=2)
        elif tier.lower() == "bulk":
            self.et = self.st + datetime.timedelta(seconds=10)
        else:
            # Standard
            self.et = self.st + datetime.timedelta(seconds=5)


class ArchiveJob(Job):
    def __init__(self, job_id, tier, arn, archive_id):
        self.job_id = job_id
        self.tier = tier
        self.arn = arn
        self.archive_id = archive_id
        Job.__init__(self, tier)

    def to_dict(self):
        d = {
            "Action": "ArchiveRetrieval",
            "ArchiveId": self.archive_id,
            "ArchiveSizeInBytes": 0,
            "ArchiveSHA256TreeHash": None,
            "Completed": False,
            "CreationDate": self.st.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "InventorySizeInBytes": 0,
            "JobDescription": None,
            "JobId": self.job_id,
            "RetrievalByteRange": None,
            "SHA256TreeHash": None,
            "SNSTopic": None,
            "StatusCode": "InProgress",
            "StatusMessage": None,
            "VaultARN": self.arn,
            "Tier": self.tier,
        }
        if datetime.datetime.now() > self.et:
            d["Completed"] = True
            d["CompletionDate"] = self.et.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            d["InventorySizeInBytes"] = 10000
            d["StatusCode"] = "Succeeded"
        return d


class InventoryJob(Job):
    def __init__(self, job_id, tier, arn):
        self.job_id = job_id
        self.tier = tier
        self.arn = arn
        Job.__init__(self, tier)

    def to_dict(self):
        d = {
            "Action": "InventoryRetrieval",
            "ArchiveSHA256TreeHash": None,
            "Completed": False,
            "CreationDate": self.st.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "InventorySizeInBytes": 0,
            "JobDescription": None,
            "JobId": self.job_id,
            "RetrievalByteRange": None,
            "SHA256TreeHash": None,
            "SNSTopic": None,
            "StatusCode": "InProgress",
            "StatusMessage": None,
            "VaultARN": self.arn,
            "Tier": self.tier,
        }
        if datetime.datetime.now() > self.et:
            d["Completed"] = True
            d["CompletionDate"] = self.et.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            d["InventorySizeInBytes"] = 10000
            d["StatusCode"] = "Succeeded"
        return d


class Vault(BaseModel):
    def __init__(self, vault_name, region):
        self.st = datetime.datetime.now()
        self.vault_name = vault_name
        self.region = region
        self.archives = {}
        self.jobs = {}

    @property
    def arn(self):
        return "arn:aws:glacier:{0}:012345678901:vaults/{1}".format(
            self.region, self.vault_name
        )

    def to_dict(self):
        archives_size = 0
        for k in self.archives:
            archives_size += self.archives[k]["size"]
        d = {
            "CreationDate": self.st.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "LastInventoryDate": self.st.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "NumberOfArchives": len(self.archives),
            "SizeInBytes": archives_size,
            "VaultARN": self.arn,
            "VaultName": self.vault_name,
        }
        return d

    def create_archive(self, body, description):
        archive_id = hashlib.md5(body).hexdigest()
        self.archives[archive_id] = {}
        self.archives[archive_id]["body"] = body
        self.archives[archive_id]["size"] = len(body)
        self.archives[archive_id]["sha256"] = hashlib.sha256(body).hexdigest()
        self.archives[archive_id]["creation_date"] = datetime.datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
        self.archives[archive_id]["description"] = description
        return archive_id

    def get_archive_body(self, archive_id):
        return self.archives[archive_id]["body"]

    def get_archive_list(self):
        archive_list = []
        for a in self.archives:
            archive = self.archives[a]
            aobj = {
                "ArchiveId": a,
                "ArchiveDescription": archive["description"],
                "CreationDate": archive["creation_date"],
                "Size": archive["size"],
                "SHA256TreeHash": archive["sha256"],
            }
            archive_list.append(aobj)
        return archive_list

    def delete_archive(self, archive_id):
        return self.archives.pop(archive_id)

    def initiate_job(self, job_type, tier, archive_id):
        job_id = get_job_id()

        if job_type == "inventory-retrieval":
            job = InventoryJob(job_id, tier, self.arn)
        elif job_type == "archive-retrieval":
            job = ArchiveJob(job_id, tier, self.arn, archive_id)

        self.jobs[job_id] = job
        return job_id

    def list_jobs(self):
        return self.jobs.values()

    def describe_job(self, job_id):
        return self.jobs.get(job_id)

    def job_ready(self, job_id):
        job = self.describe_job(job_id)
        jobj = job.to_dict()
        return jobj["Completed"]

    def get_job_output(self, job_id):
        job = self.describe_job(job_id)
        jobj = job.to_dict()
        if jobj["Action"] == "InventoryRetrieval":
            archives = self.get_archive_list()
            return {
                "VaultARN": self.arn,
                "InventoryDate": jobj["CompletionDate"],
                "ArchiveList": archives,
            }
        else:
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

    def initiate_job(self, vault_name, job_type, tier, archive_id):
        vault = self.get_vault(vault_name)
        job_id = vault.initiate_job(job_type, tier, archive_id)
        return job_id

    def list_jobs(self, vault_name):
        vault = self.get_vault(vault_name)
        return vault.list_jobs()


glacier_backends = {}
for region in Session().get_available_regions("glacier"):
    glacier_backends[region] = GlacierBackend(region)
for region in Session().get_available_regions("glacier", partition_name="aws-us-gov"):
    glacier_backends[region] = GlacierBackend(region)
for region in Session().get_available_regions("glacier", partition_name="aws-cn"):
    glacier_backends[region] = GlacierBackend(region)
