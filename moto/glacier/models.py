import hashlib

import datetime

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict
from moto.utilities.utils import md5_hash

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
    def __init__(self, vault_name, account_id, region):
        self.st = datetime.datetime.now()
        self.vault_name = vault_name
        self.region = region
        self.archives = {}
        self.jobs = {}
        self.arn = f"arn:aws:glacier:{region}:{account_id}:vaults/{vault_name}"

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
        archive_id = md5_hash(body).hexdigest()
        self.archives[archive_id] = {}
        self.archives[archive_id]["archive_id"] = archive_id
        self.archives[archive_id]["body"] = body
        self.archives[archive_id]["size"] = len(body)
        self.archives[archive_id]["sha256"] = hashlib.sha256(body).hexdigest()
        self.archives[archive_id]["creation_date"] = datetime.datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
        self.archives[archive_id]["description"] = description
        return self.archives[archive_id]

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
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.vaults = {}

    def get_vault(self, vault_name):
        return self.vaults[vault_name]

    def create_vault(self, vault_name):
        self.vaults[vault_name] = Vault(vault_name, self.account_id, self.region_name)

    def list_vaults(self):
        return self.vaults.values()

    def delete_vault(self, vault_name):
        self.vaults.pop(vault_name)

    def initiate_job(self, vault_name, job_type, tier, archive_id):
        vault = self.get_vault(vault_name)
        job_id = vault.initiate_job(job_type, tier, archive_id)
        return job_id

    def describe_job(self, vault_name, archive_id):
        vault = self.get_vault(vault_name)
        return vault.describe_job(archive_id)

    def list_jobs(self, vault_name):
        vault = self.get_vault(vault_name)
        return vault.list_jobs()

    def get_job_output(self, vault_name, job_id):
        vault = self.get_vault(vault_name)
        if vault.job_ready(job_id):
            return vault.get_job_output(job_id)
        else:
            return None

    def upload_archive(self, vault_name, body, description):
        vault = self.get_vault(vault_name)
        return vault.create_archive(body, description)


glacier_backends = BackendDict(GlacierBackend, "glacier")
