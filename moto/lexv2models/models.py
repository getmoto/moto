"""LexModelsV2Backend class with methods for supported APIs."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend

from ..utilities.tagging_service import TaggingService


class FakeBot:
    failure_reasons: List[str]

    def __init__(
        self,
        account_id: str,
        region_name: str,
        bot_name: str,
        description: str,
        role_arn: str,
        data_privacy: Optional[Dict[str, Any]],
        idle_session_ttl_in_seconds: int,
        bot_type: str,
        bot_members: Optional[Dict[str, Any]],
    ):
        self.account_id = account_id
        self.region_name = region_name

        self.id = str(uuid.uuid4())
        self.bot_name = bot_name
        self.description = description
        self.role_arn = role_arn
        self.data_privacy = data_privacy
        self.idle_session_ttl_in_seconds = idle_session_ttl_in_seconds
        self.bot_type = bot_type
        self.bot_members = bot_members
        self.status = "CREATING"
        self.creation_date_time = datetime.now().isoformat()
        self.last_updated_date_time = datetime.now().isoformat()
        self.failure_reasons = []

        self.arn = self._generate_arn()

    def _generate_arn(self) -> str:
        return f"arn:aws:lex:{self.region_name}:{self.account_id}:bot/{self.id}"


class FakeBotAlias:
    parent_bot_networks: List[str]
    history_events: List[str]

    def __init__(
        self,
        account_id: str,
        region_name: str,
        bot_alias_name: str,
        description: str,
        bot_version: str,
        bot_alias_locale_settings: Optional[Dict[str, Any]],
        conversation_log_settings: Optional[Dict[str, Any]],
        sentiment_analysis_settings: Optional[Dict[str, Any]],
        bot_id: str,
    ):
        self.account_id = account_id
        self.region_name = region_name

        self.id = str(uuid.uuid4())
        self.bot_alias_name = bot_alias_name
        self.description = description
        self.bot_version = bot_version
        self.bot_alias_locale_settings = bot_alias_locale_settings
        self.conversation_log_settings = conversation_log_settings
        self.sentiment_analysis_settings = sentiment_analysis_settings
        self.status = "CREATING"
        self.bot_id = bot_id
        self.creation_date_time = datetime.now().isoformat()
        self.last_updated_date_time = datetime.now().isoformat()
        self.parent_bot_networks = []
        self.history_events = []

        self.arn = self._generate_arn()

    def _generate_arn(self) -> str:
        return f"arn:aws:lex:{self.region_name}:{self.account_id}:bot-alias/${self.bot_id}/${self.id}"


class FakeResourcePolicy:
    def __init__(self, resource_arn: str, policy: str):
        self.resource_arn = resource_arn
        self.policy = policy
        self.revision_id = str(uuid.uuid4())


class LexModelsV2Backend(BaseBackend):
    """Implementation of LexModelsV2 APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.bots: Dict[str, FakeBot] = {}
        self.bot_aliases: Dict[str, FakeBotAlias] = {}
        self.resource_policies: Dict[str, FakeResourcePolicy] = {}
        self.tagger = TaggingService()

    def create_bot(
        self,
        bot_name: str,
        description: str,
        role_arn: str,
        data_privacy: Optional[Dict[str, Any]],
        idle_session_ttl_in_seconds: int,
        bot_tags: Optional[Dict[str, str]],
        test_bot_alias_tags: Optional[Dict[str, str]],
        bot_type: str,
        bot_members: str,
    ) -> Dict[str, Any]:
        bot = FakeBot(
            account_id=self.account_id,
            region_name=self.region_name,
            bot_name=bot_name,
            description=description,
            role_arn=role_arn,
            data_privacy=data_privacy,
            idle_session_ttl_in_seconds=idle_session_ttl_in_seconds,
            bot_type=bot_type,
            bot_members=bot_members,
        )

        self.bots[bot.id] = bot

        if bot_tags:
            self.tag_resource(bot.arn, bot_tags)

        test_alias = FakeBotAlias(
            account_id=self.account_id,
            region_name=self.region_name,
            bot_alias_name="test",
            description="test",
            bot_version="1",
            bot_alias_locale_settings={},
            conversation_log_settings={},
            sentiment_analysis_settings={},
            bot_id=bot.id,
        )
        self.bot_aliases[test_alias.id] = test_alias

        return (
            bot.id,
            bot.bot_name,
            bot.description,
            bot.role_arn,
            bot.data_privacy,
            bot.idle_session_ttl_in_seconds,
            bot.status,
            bot.creation_date_time,
            self.list_tags_for_resource(bot.arn),
            test_bot_alias_tags,
            bot.bot_type,
            bot.bot_members,
        )

    def describe_bot(self, bot_id) -> str:
        bot = self.bots[bot_id]

        return (
            bot.id,
            bot.bot_name,
            bot.description,
            bot.role_arn,
            bot.data_privacy,
            bot.idle_session_ttl_in_seconds,
            bot.status,
            bot.creation_date_time,
            bot.last_updated_date_time,
            bot.bot_type,
            bot.bot_members,
            bot.failure_reasons,
        )

    def update_bot(
        self,
        bot_id,
        bot_name,
        description,
        role_arn,
        data_privacy,
        idle_session_ttl_in_seconds,
        bot_type,
        bot_members,
    ) -> str:
        bot = self.bots[bot_id]

        bot.bot_name = bot_name
        bot.description = description
        bot.role_arn = role_arn
        bot.data_privacy = data_privacy
        bot.idle_session_ttl_in_seconds = idle_session_ttl_in_seconds
        bot.bot_type = bot_type
        bot.bot_members = bot_members
        bot.last_updated_date_time = datetime.now().isoformat()

        return (
            bot.id,
            bot.bot_name,
            bot.description,
            bot.role_arn,
            bot.data_privacy,
            bot.idle_session_ttl_in_seconds,
            bot.status,
            bot.creation_date_time,
            bot.last_updated_date_time,
            bot.bot_type,
            bot.bot_members,
        )

    def list_bots(self, sort_by, filters, max_results, next_token) -> List[Dict[str, Any]]:
        bot_summaries = [
            {
                "botId": bot.id,
                "botName": bot.bot_name,
                "description": bot.description,
                "botStatus": bot.status,
                "latestBotVersion": 1,
                "lastUpdatedDateTime": bot.last_updated_date_time,
                "botType": bot.bot_type,
            }
            for bot in self.bots.values()
        ]
        return bot_summaries, next_token

    def delete_bot(self, bot_id, skip_resource_in_use_check):
        bot = self.bots.pop(bot_id)
        return bot.id, bot.status

    def create_bot_alias(
        self,
        bot_alias_name,
        description,
        bot_version,
        bot_alias_locale_settings,
        conversation_log_settings,
        sentiment_analysis_settings,
        bot_id,
        tags,
    ):
        bot_alias = FakeBotAlias(
            self.account_id,
            self.region_name,
            bot_alias_name,
            description,
            bot_version,
            bot_alias_locale_settings,
            conversation_log_settings,
            sentiment_analysis_settings,
            bot_id,
        )

        self.bot_aliases[bot_alias.id] = bot_alias

        if tags:
            self.tag_resource(bot_alias.arn, tags)

        return (
            bot_alias.id,
            bot_alias.bot_alias_name,
            bot_alias.description,
            bot_alias.bot_version,
            bot_alias.bot_alias_locale_settings,
            bot_alias.conversation_log_settings,
            bot_alias.sentiment_analysis_settings,
            bot_alias.status,
            bot_alias.bot_id,
            bot_alias.creation_date_time,
            self.list_tags_for_resource(bot_alias.arn),
        )

    def describe_bot_alias(self, bot_alias_id, bot_id):
        ba = self.bot_aliases[bot_alias_id]

        return (
            ba.id,
            ba.bot_alias_name,
            ba.description,
            ba.bot_version,
            ba.bot_alias_locale_settings,
            ba.conversation_log_settings,
            ba.sentiment_analysis_settings,
            ba.history_events,
            ba.status,
            ba.bot_id,
            ba.creation_date_time,
            ba.last_updated_date_time,
            ba.parent_bot_networks,
        )

    def update_bot_alias(
        self,
        bot_alias_id,
        bot_alias_name,
        description,
        bot_version,
        bot_alias_locale_settings,
        conversation_log_settings,
        sentiment_analysis_settings,
        bot_id,
    ):
        ba = self.bot_aliases[bot_alias_id]

        ba.bot_alias_name = bot_alias_name
        ba.description = description
        ba.bot_version = bot_version
        ba.bot_alias_locale_settings = bot_alias_locale_settings
        ba.conversation_log_settings = conversation_log_settings
        ba.sentiment_analysis_settings = sentiment_analysis_settings
        ba.bot_id = bot_id
        ba.last_updated_date_time = datetime.now().isoformat()

        return (
            bot_alias_id,
            ba.bot_alias_name,
            ba.description,
            ba.bot_version,
            ba.bot_alias_locale_settings,
            ba.conversation_log_settings,
            ba.sentiment_analysis_settings,
            ba.status,
            ba.bot_id,
            ba.creation_date_time,
            ba.last_updated_date_time,
        )

    def list_bot_aliases(self, bot_id, max_results, next_token):
        bot_alias_summaries = [
            {
                "botAliasId": ba.id,
                "botAliasName": ba.bot_alias_name,
                "description": ba.description,
                "botVersion": ba.bot_version,
                "botAliasStatus": ba.status,
                "creationDateTime": ba.creation_date_time,
                "lastUpdatedDateTime": ba.last_updated_date_time,
            }
            for ba in self.bot_aliases.values()
        ]

        return bot_alias_summaries, next_token, bot_id

    def delete_bot_alias(self, bot_alias_id, bot_id, skip_resource_in_use_check):
        ba = self.bot_aliases.pop(bot_alias_id)
        return ba.id, ba.bot_id, ba.status

    def create_resource_policy(self, resource_arn, policy):
        rp = FakeResourcePolicy(resource_arn, policy)
        self.resource_policies[rp.resource_arn] = rp
        return rp.resource_arn, rp.revision_id

    def describe_resource_policy(self, resource_arn):
        rp = self.resource_policies[resource_arn]
        return rp.resource_arn, rp.policy, rp.revision_id

    def update_resource_policy(self, resource_arn, policy, expected_revision_id):
        rp = self.resource_policies[resource_arn]
        if expected_revision_id != rp.revision_id:
            raise Exception("Revision ID mismatch")
        rp.policy = policy
        rp.revision_id = str(uuid.uuid4())
        return rp.resource_arn, rp.revision_id

    def delete_resource_policy(self, resource_arn, expected_revision_id):
        rp = self.resource_policies[resource_arn]
        if expected_revision_id != rp.revision_id:
            raise Exception("Revision ID mismatch")
        rp = self.resource_policies.pop(resource_arn)
        return rp.resource_arn, rp.revision_id

    def tag_resource(self, resource_arn: str, tags: Dict[str, str]) -> None:
        tags_list = [{"Key": k, "Value": v} for k, v in tags.items()]
        self.tagger.tag_resource(resource_arn, tags_list)

    def untag_resource(self, resource_arn: str, tag_keys: List[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def list_tags_for_resource(self, resource_arn: str) -> Dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(resource_arn)


lexv2models_backends = BackendDict(LexModelsV2Backend, "lexv2-models")
