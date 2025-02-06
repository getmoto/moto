"""LexModelsV2Backend class with methods for supported APIs."""

from moto.core.base_backend import BackendDict, BaseBackend
from moto.utilities.utils import get_partition
from typing import Any, Dict, List, Optional, Tuple

from ..utilities.tagging_service import TaggingService


import uuid
from datetime import datetime


class FakeBot:
    def __init__(
        self,
        account_id: str,
        region_name: str,
        bot_name,
        description,
        role_arn,
        data_privacy,
        idle_session_ttl_in_seconds,
        bot_type,
        bot_members,
    ):
        self.account_id = account_id
        self.region_name = region_name

        self.bot_id = str(uuid.uuid4())
        self.bot_name = bot_name
        self.description = description
        self.role_arn = role_arn
        self.data_privacy = data_privacy
        self.idle_session_ttl_in_seconds = idle_session_ttl_in_seconds
        self.bot_type = bot_type
        self.bot_members = bot_members
        self.bot_status = "CREATING"
        self.creation_date_time = datetime.now().isoformat()
        self.last_updated_date_time = datetime.now().isoformat()
        self.failure_reasons = []
        # self.arn = self._generate_arn()

    # def _generate_arn(self) -> str:
    #     return f"arn:aws:lex:{self.region_name}:{self.account_id}:bot/{self.bot_id}"


class FakeBotAlias:
    def __init__(
        self,
        bot_alias_name,
        description,
        bot_version,
        bot_alias_locale_settings,
        conversation_log_settings,
        sentiment_analysis_settings,
        bot_id,
    ):
        self.id = str(uuid.uuid4())
        self.name = bot_alias_name
        self.description = description
        self.version = bot_version
        self.locale_settings = bot_alias_locale_settings
        self.conversation_log_settings = conversation_log_settings
        self.sentiment_analysis_settings = sentiment_analysis_settings
        self.status = "CREATING"
        self.bot_id = bot_id
        self.creation_date_time = datetime.now().isoformat()
        self.last_updated_date_time = None
        self.parent_bot_networks = []
        self.history_events = []


class LexModelsV2Backend(BaseBackend):
    """Implementation of LexModelsV2 APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.bots: Dict[str, FakeBot] = {}
        self.bot_aliases: Dict[str, FakeBotAlias] = {}
        # self.tagger = TaggingService()

    # add methods from here

    def create_bot(
        self,
        bot_name,
        description,
        role_arn,
        data_privacy,
        idle_session_ttl_in_seconds,
        bot_tags,
        test_bot_alias_tags,
        bot_type,
        bot_members,
    ):

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

        self.bots[bot.bot_id] = bot
        print("Bot ID1:", bot.bot_id)

        return (
            bot.bot_id,
            bot.bot_name,
            bot.description,
            bot.role_arn,
            bot.data_privacy,
            bot.idle_session_ttl_in_seconds,
            bot.bot_status,
            bot.creation_date_time,
            bot_tags,  # TODO: Add tags
            test_bot_alias_tags,  # TODO: Add tags
            bot.bot_type,
            bot.bot_members,
        )

    def describe_bot(self, bot_id):
        print("Bot ID2:", bot_id)

        bot = self.bots[bot_id]

        return (
            bot.bot_id,
            bot.bot_name,
            bot.description,
            bot.role_arn,
            bot.data_privacy,
            bot.idle_session_ttl_in_seconds,
            bot.bot_status,
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
    ):
        # implement here
        return (
            bot_id,
            bot_name,
            description,
            role_arn,
            data_privacy,
            idle_session_ttl_in_seconds,
            bot_status,
            creation_date_time,
            last_updated_date_time,
            bot_type,
            bot_members,
        )

    def list_bots(self, sort_by, filters, max_results, next_token):
        # implement here
        return bot_summaries, next_token

    def delete_bot(self, bot_id, skip_resource_in_use_check):
        # implement here
        return bot_id, bot_status

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
            bot_alias_name,
            description,
            bot_version,
            bot_alias_locale_settings,
            conversation_log_settings,
            sentiment_analysis_settings,
            bot_id,
        )

        self.bot_aliases[bot_alias.id] = bot_alias

        return (
            bot_alias.id,
            bot_alias.name,
            bot_alias.description,
            bot_alias.version,
            bot_alias.locale_settings,
            bot_alias.conversation_log_settings,
            bot_alias.sentiment_analysis_settings,
            bot_alias.status,
            bot_alias.bot_id,
            bot_alias.creation_date_time,
            tags,
        )

    def describe_bot_alias(self, bot_alias_id, bot_id):

        ba = self.bot_aliases[bot_alias_id]

        return (
            ba.id,
            ba.name,
            ba.description,
            ba.version,
            ba.locale_settings,
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
        # implement here
        return (
            bot_alias_id,
            bot_alias_name,
            description,
            bot_version,
            bot_alias_locale_settings,
            conversation_log_settings,
            sentiment_analysis_settings,
            bot_alias_status,
            bot_id,
            creation_date_time,
            last_updated_date_time,
        )

    def list_bot_aliases(self, bot_id, max_results, next_token):
        # implement here
        return bot_alias_summaries, next_token, bot_id

    def delete_bot_alias(self, bot_alias_id, bot_id, skip_resource_in_use_check):
        # implement here
        return bot_alias_id, bot_id, bot_alias_status

    def create_resource_policy(self, resource_arn, policy):
        # implement here
        return resource_arn, revision_id

    def describe_resource_policy(self, resource_arn):
        # implement here
        return resource_arn, policy, revision_id

    def update_resource_policy(self, resource_arn, policy, expected_revision_id):
        # implement here
        return resource_arn, revision_id

    def delete_resource_policy(self, resource_arn, expected_revision_id):
        # implement here
        return resource_arn, revision_id

    def tag_resource(self, resource_arn, tags):
        # implement here
        return

    def untag_resource(self, resource_arn, tag_keys):
        # implement here
        return

    def list_tags_for_resource(self, resource_arn):
        # implement here
        return tags


lexv2models_backends = BackendDict(LexModelsV2Backend, "lexv2-models")
