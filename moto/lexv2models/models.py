"""LexModelsV2Backend class with methods for supported APIs."""

from moto.core.base_backend import BackendDict, BaseBackend


class LexModelsV2Backend(BaseBackend):
    """Implementation of LexModelsV2 APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)

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
            bot_tags,
            test_bot_alias_tags,
            bot_type,
            bot_members,
        )

    def describe_bot(self, bot_id):
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
            failure_reasons,
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
            tags,
        )

    def describe_bot_alias(self, bot_alias_id, bot_id):
        # implement here
        return (
            bot_alias_id,
            bot_alias_name,
            description,
            bot_version,
            bot_alias_locale_settings,
            conversation_log_settings,
            sentiment_analysis_settings,
            bot_alias_history_events,
            bot_alias_status,
            bot_id,
            creation_date_time,
            last_updated_date_time,
            parent_bot_networks,
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
