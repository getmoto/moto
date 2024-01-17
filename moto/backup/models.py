"""BackupBackend class with methods for supported APIs."""

from typing import Dict, Any, List

from moto.core import BaseBackend, BackendDict, BaseModel
from moto.utilities.tagging_service import TaggingService
from moto.core.utils import unix_time
from moto.moto_api._internal import mock_random
from .exceptions import (
    AlreadyExistsException,
    ResourceNotFoundException,
)

class Plan(BaseModel):
    def __init__(
        self,
        backup_plan: Dict[str, Any],
        creator_request_id: str,
        backend: "BackupBackend",
    ):
        self.backup_plan_id = str(mock_random.uuid4())
        self.backup_plan_arn = f"arn:aws:backup:{backend.region_name}:{backend.account_id}:backup-plan:{self.backup_plan_id}"
        self.creation_date = unix_time()
        self.version_id = self.random_str_utf8()
        self.creator_request_id = creator_request_id
        self.backup_plan = backup_plan
        adv_settings = backup_plan.get("AdvancedBackupSettings")
        self.advanced_backup_settings = adv_settings or []

    def to_dict(self) -> Dict[str, Any]:
        dct = {
            "BackupPlanId": self.backup_plan_id,
            "BackupPlanArn": self.backup_plan_arn,
            "CreationDate": self.creation_date,
            "VersionId": self.version_id,
            "AdvancedBackupSettings": self.advanced_backup_settings,
        }
        return {k: v for k, v in dct.items() if v}
    
    def to_get_dict(self) -> Dict[str, Any]:
        dct = self.to_dict()
        dct_options = {
            "BackupPlan": self.backup_plan,
            "CreatorRequestId": self.creator_request_id,
            "DeletionDate": unix_time(),# need to find deletion and lastexecutiondate
            "LastExecutionDate": unix_time()
        }
        for key, value in dct_options.items():
            if value is not None:
                dct[key] = value
        return dct
    
    def to_list_dict(self) -> Dict[str, Any]:
        dct = self.to_get_dict()
        dct.pop("BackupPlan")
        dct["BackupPlanName"] = self.backup_plan.get("BackupPlanName")
        return dct
    
    def random_str_utf8(self) -> str:
        ran_str = mock_random.get_random_string(length=48)
        utf8_bytes = ran_str.encode('utf-8')
        return utf8_bytes.decode('utf-8')

class Vault(BaseModel):
    def __init__(
        self,
        backup_vault_name: str,
        encryption_key_arn: str,
        creator_request_id: str,
        backend: "BackupBackend",
    ):
        self.backup_vault_name = backup_vault_name
        self.backup_vault_arn = f"arn:aws:backup:{backend.region_name}:{backend.account_id}:backup-vault:{backup_vault_name}"
        self.creation_date = unix_time()
        self.vault_type = "BACKUP_VAULT" # This will be different for create_logically_air_gapped_backup_vault
        self.encryption_key_arn = encryption_key_arn
        self.creator_request_id = creator_request_id
        self.num_of_recovery_points = 0 # How to get this value??
        self.locked = True # initiate vault lock
        self.min_retention_days = 0 # initiate vault lock
        self.max_retention_days = 0 # initiate vault lock
        self.lock_date = unix_time() # initiate vault lock

    def to_dict(self) -> Dict[str, Any]:
        dct = {
            "BackupVaultName": self.backup_vault_name,
            "BackupVaultArn": self.backup_vault_arn,
            "CreationDate": self.creation_date,
        }
        return dct
    
    def to_desc_dict(self) -> Dict[str, Any]:
        dct = self.to_dict()
        dct_options: Dict[str, Any] = dict()
        dct_options = {
            "VaultType": self.vault_type,
            "EncryptionKeyArn": self.encryption_key_arn,
            "CreatorRequestId": self.creator_request_id,
            "NumberOfRecoveryPoints": self.num_of_recovery_points,
            "Locked": self.locked,
            "MinRetentionDays": self.min_retention_days,
            "MaxRetentionDays": self.max_retention_days,
            "LockDate": self.lock_date
        }
        for key, value in dct_options.items():
            if value is not None:
                dct[key] = value
        return dct

    def to_list_dict(self) -> Dict[str, Any]:
        dct = self.to_desc_dict()
        dct.pop("VaultType")
        return dct

class BackupBackend(BaseBackend):
    """Implementation of Backup APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)

        self.vaults: Dict[str, Vault] = dict()
        self.plans: Dict[str, Plan] = dict()
        self.tagger = TaggingService()

    # def _get_vault(self, name: str = "") -> bool:
    #     if name in self.vaults:
    #         return self.vaults[name]

    def create_backup_plan(self, backup_plan: Dict[str, Any], backup_plan_tags: Dict[str, str], creator_request_id: str) -> Plan:
        plan = Plan(
            backup_plan=backup_plan,
            creator_request_id=creator_request_id,
            backend=self,
        )
        if backup_plan_tags:
            self.tag_resource(plan.backup_plan_arn, backup_plan_tags)
        self.plans[plan.backup_plan_id] = plan
        return plan
    
    def create_backup_vault(self, backup_vault_name: str, backup_vault_tags: Dict[str, str], encryption_key_arn: str, creator_request_id: str) -> Vault:
        # try:
        #     self._get_vault(name=backup_vault_name)
        #     raise AlreadyExistsException(
        #         message="Backup vault with the same name already exists"
        #     )
        # except ResourceNotFoundException: ## need more work
        #     pass
    
        vault = Vault(
            backup_vault_name=backup_vault_name,
            encryption_key_arn=encryption_key_arn,
            creator_request_id=creator_request_id,
            backend=self,
        )
        if backup_vault_tags:
            self.tag_resource(vault.backup_vault_arn, backup_vault_tags)
        self.vaults[backup_vault_name] = vault
        return vault
    
    def get_backup_plan(self, backup_plan_id: str, version_id: str) -> Plan:
       if backup_plan_id not in self.plans:
            raise ResourceNotFoundException(backup_plan_id)
       return self.plans[backup_plan_id]

    def describe_backup_vault(self, backup_vault_name: str, backup_vault_account_id: str) -> Vault:
        
       if backup_vault_name not in self.vaults:
            raise ResourceNotFoundException(backup_vault_name) # Accessdenied exception
       return self.vaults[backup_vault_name]
    
    def delete_backup_plan(self, backup_plan_id) -> str:
        if backup_plan_id not in self.plans:
            raise ResourceNotFoundException(backup_plan_id)
        deletion_date = unix_time()
        res = self.plans.pop(backup_plan_id)
        return res.backup_plan_id, res.backup_plan_arn, deletion_date, res.version_id
    
    def list_backup_plans(self) -> List[Plan]:
        """
        Pagination is not yet implemented
        """
        return list(self.plans.values())
    
    def list_backup_vaults(self) -> List[Vault]:
        """
        Pagination is not yet implemented
        """
        return list(self.vaults.values())
    
    def list_tags(self, resource_arn: str) -> Dict[str, str]:
        """
        Pagination is not yet implemented
        """
        return self.tagger.get_tag_dict_for_resource(resource_arn)
     
    def tag_resource(self, resource_arn: str, tags: Dict[str, str]) -> None:
        tags_input = TaggingService.convert_dict_to_tags_input(tags or {})
        self.tagger.tag_resource(resource_arn, tags_input)
    
    def untag_resource(self, resource_arn: str, tag_key_list: List[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_key_list)
    

backup_backends = BackendDict(BackupBackend, "backup")
