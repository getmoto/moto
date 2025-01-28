"""Handles incoming lexv2models requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import lexv2models_backends


class LexModelsV2Response(BaseResponse):
    """Handler for LexModelsV2 requests and responses."""

    def __init__(self):
        super().__init__(service_name="lexv2models")

    @property
    def lexv2models_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # lexv2models_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return lexv2models_backends[self.current_account][self.region]

    # add methods from here

    def create_bot(self):
        params = self._get_params()
        bot_name = params.get("botName")
        description = params.get("description")
        role_arn = params.get("roleArn")
        data_privacy = params.get("dataPrivacy")
        idle_session_ttl_in_seconds = params.get("idleSessionTTLInSeconds")
        bot_tags = params.get("botTags")
        test_bot_alias_tags = params.get("testBotAliasTags")
        bot_type = params.get("botType")
        bot_members = params.get("botMembers")
        (
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
        ) = self.lexv2models_backend.create_bot(
            bot_name=bot_name,
            description=description,
            role_arn=role_arn,
            data_privacy=data_privacy,
            idle_session_ttl_in_seconds=idle_session_ttl_in_seconds,
            bot_tags=bot_tags,
            test_bot_alias_tags=test_bot_alias_tags,
            bot_type=bot_type,
            bot_members=bot_members,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                botId=bot_id,
                botName=bot_name,
                description=description,
                roleArn=role_arn,
                dataPrivacy=data_privacy,
                idleSessionTtlInSeconds=idle_session_ttl_in_seconds,
                botStatus=bot_status,
                creationDateTime=creation_date_time,
                botTags=bot_tags,
                testBotAliasTags=test_bot_alias_tags,
                botType=bot_type,
                botMembers=bot_members,
            )
        )

    def describe_bot(self):
        params = self._get_params()
        bot_id = params.get("botId")
        (
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
        ) = self.lexv2models_backend.describe_bot(
            bot_id=bot_id,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                botId=bot_id,
                botName=bot_name,
                description=description,
                roleArn=role_arn,
                dataPrivacy=data_privacy,
                idleSessionTtlInSeconds=idle_session_ttl_in_seconds,
                botStatus=bot_status,
                creationDateTime=creation_date_time,
                lastUpdatedDateTime=last_updated_date_time,
                botType=bot_type,
                botMembers=bot_members,
                failureReasons=failure_reasons,
            )
        )

    # add templates from here

    def update_bot(self):
        params = self._get_params()
        bot_id = params.get("botId")
        bot_name = params.get("botName")
        description = params.get("description")
        role_arn = params.get("roleArn")
        data_privacy = params.get("dataPrivacy")
        idle_session_ttl_in_seconds = params.get("idleSessionTTLInSeconds")
        bot_type = params.get("botType")
        bot_members = params.get("botMembers")
        (
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
        ) = self.lexv2models_backend.update_bot(
            bot_id=bot_id,
            bot_name=bot_name,
            description=description,
            role_arn=role_arn,
            data_privacy=data_privacy,
            idle_session_ttl_in_seconds=idle_session_ttl_in_seconds,
            bot_type=bot_type,
            bot_members=bot_members,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                botId=bot_id,
                botName=bot_name,
                description=description,
                roleArn=role_arn,
                dataPrivacy=data_privacy,
                idleSessionTtlInSeconds=idle_session_ttl_in_seconds,
                botStatus=bot_status,
                creationDateTime=creation_date_time,
                lastUpdatedDateTime=last_updated_date_time,
                botType=bot_type,
                botMembers=bot_members,
            )
        )

    def list_bots(self):
        params = self._get_params()
        sort_by = params.get("sortBy")
        filters = params.get("filters")
        max_results = params.get("maxResults")
        next_token = params.get("nextToken")
        bot_summaries, next_token = self.lexv2models_backend.list_bots(
            sort_by=sort_by,
            filters=filters,
            max_results=max_results,
            next_token=next_token,
        )
        # TODO: adjust response
        return json.dumps(dict(botSummaries=bot_summaries, nextToken=next_token))

    def delete_bot(self):
        params = self._get_params()
        bot_id = params.get("botId")
        skip_resource_in_use_check = params.get("skipResourceInUseCheck")
        bot_id, bot_status = self.lexv2models_backend.delete_bot(
            bot_id=bot_id,
            skip_resource_in_use_check=skip_resource_in_use_check,
        )
        # TODO: adjust response
        return json.dumps(dict(botId=bot_id, botStatus=bot_status))

    def create_bot_alias(self):
        params = self._get_params()
        bot_alias_name = params.get("botAliasName")
        description = params.get("description")
        bot_version = params.get("botVersion")
        bot_alias_locale_settings = params.get("botAliasLocaleSettings")
        conversation_log_settings = params.get("conversationLogSettings")
        sentiment_analysis_settings = params.get("sentimentAnalysisSettings")
        bot_id = params.get("botId")
        tags = params.get("tags")
        (
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
        ) = self.lexv2models_backend.create_bot_alias(
            bot_alias_name=bot_alias_name,
            description=description,
            bot_version=bot_version,
            bot_alias_locale_settings=bot_alias_locale_settings,
            conversation_log_settings=conversation_log_settings,
            sentiment_analysis_settings=sentiment_analysis_settings,
            bot_id=bot_id,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                botAliasId=bot_alias_id,
                botAliasName=bot_alias_name,
                description=description,
                botVersion=bot_version,
                botAliasLocaleSettings=bot_alias_locale_settings,
                conversationLogSettings=conversation_log_settings,
                sentimentAnalysisSettings=sentiment_analysis_settings,
                botAliasStatus=bot_alias_status,
                botId=bot_id,
                creationDateTime=creation_date_time,
                tags=tags,
            )
        )

    def describe_bot_alias(self):
        params = self._get_params()
        bot_alias_id = params.get("botAliasId")
        bot_id = params.get("botId")
        (
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
        ) = self.lexv2models_backend.describe_bot_alias(
            bot_alias_id=bot_alias_id,
            bot_id=bot_id,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                botAliasId=bot_alias_id,
                botAliasName=bot_alias_name,
                description=description,
                botVersion=bot_version,
                botAliasLocaleSettings=bot_alias_locale_settings,
                conversationLogSettings=conversation_log_settings,
                sentimentAnalysisSettings=sentiment_analysis_settings,
                botAliasHistoryEvents=bot_alias_history_events,
                botAliasStatus=bot_alias_status,
                botId=bot_id,
                creationDateTime=creation_date_time,
                lastUpdatedDateTime=last_updated_date_time,
                parentBotNetworks=parent_bot_networks,
            )
        )

    def update_bot_alias(self):
        params = self._get_params()
        bot_alias_id = params.get("botAliasId")
        bot_alias_name = params.get("botAliasName")
        description = params.get("description")
        bot_version = params.get("botVersion")
        bot_alias_locale_settings = params.get("botAliasLocaleSettings")
        conversation_log_settings = params.get("conversationLogSettings")
        sentiment_analysis_settings = params.get("sentimentAnalysisSettings")
        bot_id = params.get("botId")
        (
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
        ) = self.lexv2models_backend.update_bot_alias(
            bot_alias_id=bot_alias_id,
            bot_alias_name=bot_alias_name,
            description=description,
            bot_version=bot_version,
            bot_alias_locale_settings=bot_alias_locale_settings,
            conversation_log_settings=conversation_log_settings,
            sentiment_analysis_settings=sentiment_analysis_settings,
            bot_id=bot_id,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                botAliasId=bot_alias_id,
                botAliasName=bot_alias_name,
                description=description,
                botVersion=bot_version,
                botAliasLocaleSettings=bot_alias_locale_settings,
                conversationLogSettings=conversation_log_settings,
                sentimentAnalysisSettings=sentiment_analysis_settings,
                botAliasStatus=bot_alias_status,
                botId=bot_id,
                creationDateTime=creation_date_time,
                lastUpdatedDateTime=last_updated_date_time,
            )
        )

    def list_bot_aliases(self):
        params = self._get_params()
        bot_id = params.get("botId")
        max_results = params.get("maxResults")
        next_token = params.get("nextToken")
        bot_alias_summaries, next_token, bot_id = (
            self.lexv2models_backend.list_bot_aliases(
                bot_id=bot_id,
                max_results=max_results,
                next_token=next_token,
            )
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                botAliasSummaries=bot_alias_summaries,
                nextToken=next_token,
                botId=bot_id,
            )
        )

    def delete_bot_alias(self):
        params = self._get_params()
        bot_alias_id = params.get("botAliasId")
        bot_id = params.get("botId")
        skip_resource_in_use_check = params.get("skipResourceInUseCheck")
        bot_alias_id, bot_id, bot_alias_status = (
            self.lexv2models_backend.delete_bot_alias(
                bot_alias_id=bot_alias_id,
                bot_id=bot_id,
                skip_resource_in_use_check=skip_resource_in_use_check,
            )
        )
        # TODO: adjust response
        return json.dumps(
            dict(botAliasId=bot_alias_id, botId=bot_id, botAliasStatus=bot_alias_status)
        )

    def create_resource_policy(self):
        params = self._get_params()
        resource_arn = params.get("resourceArn")
        policy = params.get("policy")
        resource_arn, revision_id = self.lexv2models_backend.create_resource_policy(
            resource_arn=resource_arn,
            policy=policy,
        )
        # TODO: adjust response
        return json.dumps(dict(resourceArn=resource_arn, revisionId=revision_id))

    def describe_resource_policy(self):
        params = self._get_params()
        resource_arn = params.get("resourceArn")
        resource_arn, policy, revision_id = (
            self.lexv2models_backend.describe_resource_policy(
                resource_arn=resource_arn,
            )
        )
        # TODO: adjust response
        return json.dumps(
            dict(resourceArn=resource_arn, policy=policy, revisionId=revision_id)
        )

    def update_resource_policy(self):
        params = self._get_params()
        resource_arn = params.get("resourceArn")
        policy = params.get("policy")
        expected_revision_id = params.get("expectedRevisionId")
        resource_arn, revision_id = self.lexv2models_backend.update_resource_policy(
            resource_arn=resource_arn,
            policy=policy,
            expected_revision_id=expected_revision_id,
        )
        # TODO: adjust response
        return json.dumps(dict(resourceArn=resource_arn, revisionId=revision_id))

    def delete_resource_policy(self):
        params = self._get_params()
        resource_arn = params.get("resourceArn")
        expected_revision_id = params.get("expectedRevisionId")
        resource_arn, revision_id = self.lexv2models_backend.delete_resource_policy(
            resource_arn=resource_arn,
            expected_revision_id=expected_revision_id,
        )
        # TODO: adjust response
        return json.dumps(dict(resourceArn=resource_arn, revisionId=revision_id))

    def tag_resource(self):
        params = self._get_params()
        resource_arn = params.get("resourceARN")
        tags = params.get("tags")
        self.lexv2models_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict())

    def untag_resource(self):
        params = self._get_params()
        resource_arn = params.get("resourceARN")
        tag_keys = params.get("tagKeys")
        self.lexv2models_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )
        # TODO: adjust response
        return json.dumps(dict())

    def list_tags_for_resource(self):
        params = self._get_params()
        resource_arn = params.get("resourceARN")
        tags = self.lexv2models_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(tags=tags))
