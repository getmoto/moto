import xmltodict

from moto.core.responses import BaseResponse
from .models import cloudfront_backend


XMLNS = "http://cloudfront.amazonaws.com/doc/2020-05-31/"


class CloudFrontResponse(BaseResponse):
    def _get_xml_body(self):
        return xmltodict.parse(self.body, dict_constructor=dict)

    def distributions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.create_distribution()
        if request.method == "GET":
            return self.list_distributions()

    def create_distribution(self):
        params = self._get_xml_body()
        distribution_config = params.get("DistributionConfig")
        distribution, location, e_tag = cloudfront_backend.create_distribution(
            distribution_config=distribution_config
        )
        template = self.response_template(CREATE_DISTRIBUTION_TEMPLATE)
        response = template.render(distribution=distribution, xmlns=XMLNS)
        headers = {"ETag": e_tag, "Location": location}
        return 200, headers, response

    def list_distributions(self):
        distributions = cloudfront_backend.list_distributions()
        template = self.response_template(LIST_TEMPLATE)
        response = template.render(distributions=distributions)
        return 200, {}, response

    def individual_distribution(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        distribution_id = full_url.split("/")[-1]
        if request.method == "DELETE":
            if_match = self._get_param("If-Match")
            cloudfront_backend.delete_distribution(distribution_id, if_match)
            return 204, {}, ""
        if request.method == "GET":
            dist, etag = cloudfront_backend.get_distribution(distribution_id)
            template = self.response_template(GET_DISTRIBUTION_TEMPLATE)
            response = template.render(distribution=dist, xmlns=XMLNS)
            return 200, {"ETag": etag}, response

    def update_distribution(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        params = self._get_xml_body()
        distribution_config = params.get("DistributionConfig")
        dist_id = full_url.split("/")[-2]
        if_match = headers["If-Match"]

        dist, location, e_tag = cloudfront_backend.update_distribution(
            DistributionConfig=distribution_config,
            Id=dist_id,
            IfMatch=if_match,
        )
        template = self.response_template(UPDATE_DISTRIBUTION_TEMPLATE)
        response = template.render(distribution=dist, xmlns=XMLNS)
        headers = {"ETag": e_tag, "Location": location}
        return 200, headers, response


DIST_META_TEMPLATE = """
    <Id>{{ distribution.distribution_id }}</Id>
    <ARN>{{ distribution.arn }}</ARN>
    <Status>{{ distribution.status }}</Status>
    <LastModifiedTime>{{ distribution.last_modified_time }}</LastModifiedTime>
    <InProgressInvalidationBatches>{{ distribution.in_progress_invalidation_batches }}</InProgressInvalidationBatches>
    <DomainName>{{ distribution.domain_name }}</DomainName>
"""


DIST_CONFIG_TEMPLATE = """
      <CallerReference>{{ distribution.distribution_config.caller_reference }}</CallerReference>
      <Aliases>
        <Quantity>{{ distribution.distribution_config.aliases|length }}</Quantity>
        <Items>
          {% for alias  in distribution.distribution_config.aliases %}
            <CNAME>{{ alias }}</CNAME>
          {% endfor %}
        </Items>
      </Aliases>
      <DefaultRootObject>{{ distribution.distribution_config.default_distribution_object }}</DefaultRootObject>
      <Origins>
        <Quantity>{{ distribution.distribution_config.origins|length }}</Quantity>
        <Items>
          {% for origin  in distribution.distribution_config.origins %}
          <Origin>
            <Id>{{ origin.id }}</Id>
            <DomainName>{{ origin.domain_name }}</DomainName>
            <OriginPath>{{ origin.origin_path }}</OriginPath>
            <CustomHeaders>
              <Quantity>{{ origin.custom_headers|length }}</Quantity>
              <Items>
                {% for header  in origin.custom_headers %}
                  <HeaderName>{{ header.header_name }}</HeaderName>
                  <HeaderValue>{{ header.header_value }}</HeaderValue>
                {% endfor %}
              </Items>
            </CustomHeaders>
            <S3OriginConfig>
              <OriginAccessIdentity>{{ origin.s3_access_identity }}</OriginAccessIdentity>
            </S3OriginConfig>
            {% if origin.custom_origin %}
            <CustomOriginConfig>
              <HTTPPort>{{ origin.custom_origin.http_port }}</HTTPPort>
              <HTTPSPort>{{ origin.custom_origin.https_port }}</HTTPSPort>
              <OriginProtocolPolicy>{{ OriginProtocolPolicy }}</OriginProtocolPolicy>
              <OriginSslProtocols>
                <Quantity>{{ origin.custom_origin.origin_ssl_protocols.quantity }}</Quantity>
                <Items>
                  {% for protocol  in origin.custom_origin.origin_ssl_protocols %}
                  {{ protocol }}
                  {% endfor %}
                </Items>
              </OriginSslProtocols>
              <OriginReadTimeout>{{ origin.custom_origin.origin_read_timeout }}</OriginReadTimeout>
              <OriginKeepaliveTimeout>{{ origin.custom_origin.origin_keepalive_timeout }}</OriginKeepaliveTimeout>
            </CustomOriginConfig>
            {% endif %}
            <ConnectionAttempts>{{ origin.connection_attempts }}</ConnectionAttempts>
            <ConnectionTimeout>{{ origin.connection_timeout }}</ConnectionTimeout>
            {% if origin.origin_shield %}
            <OriginShield>
              <Enabled>{{ origin.origin_shield.enabled }}</Enabled>
              <OriginShieldRegion>{{ OriginShieldRegion }}</OriginShieldRegion>
            </OriginShield>
            {% else %}
            <OriginShield>
              <Enabled>false</Enabled>
            </OriginShield>
            {% endif %}
            </Origin>
          {% endfor %}
        </Items>
      </Origins>
      <OriginGroups>
        <Quantity>{{ distribution.distribution_config.origin_groups|length }}</Quantity>
        {% if distribution.distribution_config.origin_groups %}
        <Items>
          {% for origin_group  in distribution.distribution_config.origin_groups %}
            <Id>{{ origin_group.id }}</Id>
            <FailoverCriteria>
              <StatusCodes>
                <Quantity>{{ origin_group.failover_criteria.status_codes.quantity }}</Quantity>
                <Items>
                  {% for status_code_list  in origin_group_list.failover_criteria.status_codes.StatusCodeList %}
                    <StatusCode>{{ status_code_list.status_code }}</StatusCode>
                  {% endfor %}
                </Items>
              </StatusCodes>
            </FailoverCriteria>
            <Members>
              <Quantity>{{ origin_group.members.quantity }}</Quantity>
              <Items>
                {% for origin_group_member_list  in origin_group.members.OriginGroupMemberList %}
                  <OriginId>{{ origin_group_member_list.origin_id }}</OriginId>
                {% endfor %}
              </Items>
            </Members>
          {% endfor %}
        </Items>
        {% endif %}
      </OriginGroups>
      <DefaultCacheBehavior>
        <TargetOriginId>{{ distribution.distribution_config.default_cache_behavior.target_origin_id }}</TargetOriginId>
        <TrustedSigners>
          <Enabled>{{ distribution.distribution_config.default_cache_behavior.trusted_signers.enabled }}</Enabled>
          <Quantity>{{ distribution.distribution_config.default_cache_behavior.trusted_signers|length }}</Quantity>
          <Items>
            {% for aws_account_number  in distribution.distribution_config.default_cache_behavior.trusted_signers %}
              <AwsAccountNumber>{{ aws_account_number }}</AwsAccountNumber>
            {% endfor %}
          </Items>
        </TrustedSigners>
        <TrustedKeyGroups>
          <Enabled>{{ distribution.distribution_config.default_cache_behavior.trusted_key_groups_enabled }}</Enabled>
          <Quantity>{{ distribution.distribution_config.default_cache_behavior.trusted_key_groups|length }}</Quantity>
          <Items>
            {% for key_group  in distribution.distribution_config.default_cache_behavior.trusted_key_groups %}
              <KeyGroup>{{ key_group }}</KeyGroup>
            {% endfor %}
          </Items>
        </TrustedKeyGroups>
        <ViewerProtocolPolicy>{{ distribution.distribution_config.default_cache_behavior.viewer_protocol_policy }}</ViewerProtocolPolicy>
        <AllowedMethods>
          <Quantity>{{ distribution.distribution_config.default_cache_behavior.allowed_methods|length }}</Quantity>
          <Items>
            {% for method in distribution.distribution_config.default_cache_behavior.allowed_methods %}
            <member>{{ method }}</member>
            {% endfor %}
          </Items>
          <CachedMethods>
            <Quantity>{{ distribution.distribution_config.default_cache_behavior.cached_methods|length }}</Quantity>
            <Items>
              {% for method in distribution.distribution_config.default_cache_behavior.cached_methods %}
              <member>{{ method }}</member>
              {% endfor %}
            </Items>
          </CachedMethods>
        </AllowedMethods>
        <SmoothStreaming>{{ distribution.distribution_config.default_cache_behavior.smooth_streaming }}</SmoothStreaming>
        <Compress>{{ 'true' if distribution.distribution_config.default_cache_behavior.compress else 'false' }}</Compress>
        <LambdaFunctionAssociations>
          <Quantity>{{ distribution.distribution_config.default_cache_behavior.lambda_function_associations|length }}</Quantity>
          {% if distribution.distribution_config.default_cache_behavior.lambda_function_associations %}
          <Items>
            {% for func in distribution.distribution_config.default_cache_behavior.lambda_function_associations %}
              <LambdaFunctionARN>{{ func.arn }}</LambdaFunctionARN>
              <EventType>{{ func.event_type }}</EventType>
              <IncludeBody>{{ func.include_body }}</IncludeBody>
            {% endfor %}
          </Items>
          {% endif %}
        </LambdaFunctionAssociations>
        <FunctionAssociations>
          <Quantity>{{ distribution.distribution_config.default_cache_behavior.function_associations|length }}</Quantity>
          {% if distribution.distribution_config.default_cache_behavior.function_associations %}
          <Items>
            {% for func in distribution.distribution_config.default_cache_behavior.function_associations %}
              <FunctionARN>{{ func.arn }}</FunctionARN>
              <EventType>{{ func.event_type }}</EventType>
            {% endfor %}
          </Items>
          {% endif %}
        </FunctionAssociations>
        <FieldLevelEncryptionId>{{ distribution.distribution_config.default_cache_behavior.field_level_encryption_id }}</FieldLevelEncryptionId>
        <RealtimeLogConfigArn>{{ distribution.distribution_config.default_cache_behavior.realtime_log_config_arn }}</RealtimeLogConfigArn>
        <CachePolicyId>{{ distribution.distribution_config.default_cache_behavior.cache_policy_id }}</CachePolicyId>
        <OriginRequestPolicyId>{{ distribution.distribution_config.default_cache_behavior.origin_request_policy_id }}</OriginRequestPolicyId>
        <ResponseHeadersPolicyId>{{ distribution.distribution_config.default_cache_behavior.response_headers_policy_id }}</ResponseHeadersPolicyId>
        <ForwardedValues>
          <QueryString>{{ distribution.distribution_config.default_cache_behavior.forwarded_values.query_string }}</QueryString>
          <Cookies>
            <Forward>{{ ItemSelection }}</Forward>
            <WhitelistedNames>
              <Quantity>{{ distribution.distribution_config.default_cache_behavior.forwarded_values.whitelisted_names|length }}</Quantity>
              <Items>
                {% for name  in distribution.distribution_config.default_cache_behavior.forwarded_values.whitelisted_names %}
                  <Name>{{ name }}</Name>
                {% endfor %}
              </Items>
            </WhitelistedNames>
          </Cookies>
          <Headers>
            <Quantity>{{ distribution.distribution_config.default_cache_behavior.forwarded_values.headers|length }}</Quantity>
            <Items>
              {% for h  in distribution.distribution_config.default_cache_behavior.forwarded_values.headers %}
                <Name>{{ h }}</Name>
              {% endfor %}
            </Items>
          </Headers>
          <QueryStringCacheKeys>
            <Quantity>{{ distribution.distribution_config.default_cache_behavior.forwarded_values.query_string_cache_keys|length }}</Quantity>
            <Items>
              {% for key  in distribution.distribution_config.default_cache_behavior.forwarded_values.query_string_cache_keys %}
                <Name>{{ key }}</Name>
              {% endfor %}
            </Items>
          </QueryStringCacheKeys>
        </ForwardedValues>
        <MinTTL>{{ distribution.distribution_config.default_cache_behavior.min_ttl }}</MinTTL>
        <DefaultTTL>{{ distribution.distribution_config.default_cache_behavior.default_ttl }}</DefaultTTL>
        <MaxTTL>{{ distribution.distribution_config.default_cache_behavior.max_ttl }}</MaxTTL>
      </DefaultCacheBehavior>
      <CacheBehaviors>
        <Quantity>{{ distribution.distribution_config.cache_behaviors|length }}</Quantity>
        {% if distribution.distribution_config.cache_behaviors %}
        <Items>
          {% for behaviour  in distribution.distribution_config.cache_behaviors %}
            <PathPattern>{{ behaviour.path_pattern }}</PathPattern>
            <TargetOriginId>{{ behaviour.target_origin_id }}</TargetOriginId>
            <TrustedSigners>
              <Enabled>{{ behaviour.trusted_signers.enabled }}</Enabled>
              <Quantity>{{ behaviour.trusted_signers.quantity }}</Quantity>
              <Items>
                {% for account_nr  in behaviour.trusted_signers %}
                  <AwsAccountNumber>{{ account_nr }}</AwsAccountNumber>
                {% endfor %}
              </Items>
            </TrustedSigners>
            <TrustedKeyGroups>
              <Enabled>{{ cache_behavior_list.trusted_key_groups.enabled }}</Enabled>
              <Quantity>{{ cache_behavior_list.trusted_key_groups.quantity }}</Quantity>
              <Items>
                {% for trusted_key_group_id_list  in cache_behavior_list.trusted_key_groups.TrustedKeyGroupIdList %}
                  <KeyGroup>{{ trusted_key_group_id_list.key_group }}</KeyGroup>
                {% endfor %}
              </Items>
            </TrustedKeyGroups>
            <ViewerProtocolPolicy>{{ ViewerProtocolPolicy }}</ViewerProtocolPolicy>
            <AllowedMethods>
              <Quantity>{{ cache_behavior_list.allowed_methods.quantity }}</Quantity>
              <Items>
                {% for methods_list  in cache_behavior_list.allowed_methods.MethodsList %}{{ Method }}{% endfor %}
              </Items>
              <CachedMethods>
                <Quantity>{{ cache_behavior_list.allowed_methods.cached_methods.quantity }}</Quantity>
                <Items>
                  {% for methods_list  in cache_behavior_list.allowed_methods.cached_methods.MethodsList %}{{ Method }}{% endfor %}
                </Items>
              </CachedMethods>
            </AllowedMethods>
            <SmoothStreaming>{{ cache_behavior_list.smooth_streaming }}</SmoothStreaming>
            <Compress>{{ cache_behavior_list.compress }}</Compress>
            <LambdaFunctionAssociations>
              <Quantity>{{ cache_behavior_list.lambda_function_associations.quantity }}</Quantity>
              <Items>
                {% for lambda_function_association_list  in cache_behavior_list.lambda_function_associations.LambdaFunctionAssociationList %}
                  <LambdaFunctionARN>{{ LambdaFunctionARN }}</LambdaFunctionARN>
                  <EventType>{{ EventType }}</EventType>
                  <IncludeBody>{{ lambda_function_association_list.include_body }}</IncludeBody>
                {% endfor %}
              </Items>
            </LambdaFunctionAssociations>
            <FunctionAssociations>
              <Quantity>{{ cache_behavior_list.function_associations.quantity }}</Quantity>
              <Items>
                {% for function_association_list  in cache_behavior_list.function_associations.FunctionAssociationList %}
                  <FunctionARN>{{ FunctionARN }}</FunctionARN>
                  <EventType>{{ EventType }}</EventType>
                {% endfor %}
              </Items>
            </FunctionAssociations>
            <FieldLevelEncryptionId>{{ cache_behavior_list.field_level_encryption_id }}</FieldLevelEncryptionId>
            <RealtimeLogConfigArn>{{ cache_behavior_list.realtime_log_config_arn }}</RealtimeLogConfigArn>
            <CachePolicyId>{{ cache_behavior_list.cache_policy_id }}</CachePolicyId>
            <OriginRequestPolicyId>{{ cache_behavior_list.origin_request_policy_id }}</OriginRequestPolicyId>
            <ResponseHeadersPolicyId>{{ cache_behavior_list.response_headers_policy_id }}</ResponseHeadersPolicyId>
            <ForwardedValues>
              <QueryString>{{ cache_behavior_list.forwarded_values.query_string }}</QueryString>
              <Cookies>
                <Forward>{{ ItemSelection }}</Forward>
                <WhitelistedNames>
                  <Quantity>{{ cache_behavior_list.forwarded_values.cookies.whitelisted_names.quantity }}</Quantity>
                  <Items>
                    {% for cookie_name_list  in cache_behavior_list.forwarded_values.cookies.whitelisted_names.CookieNameList %}
                      <Name>{{ cookie_name_list.name }}</Name>
                    {% endfor %}
                  </Items>
                </WhitelistedNames>
              </Cookies>
              <Headers>
                <Quantity>{{ cache_behavior_list.forwarded_values.headers.quantity }}</Quantity>
                <Items>
                  {% for header_list  in cache_behavior_list.forwarded_values.headers.HeaderList %}
                    <Name>{{ header_list.name }}</Name>
                  {% endfor %}
                </Items>
              </Headers>
              <QueryStringCacheKeys>
                <Quantity>{{ cache_behavior_list.forwarded_values.query_string_cache_keys.quantity }}</Quantity>
                <Items>
                  {% for query_string_cache_keys_list  in cache_behavior_list.forwarded_values.query_string_cache_keys.QueryStringCacheKeysList %}
                    <Name>{{ query_string_cache_keys_list.name }}</Name>
                  {% endfor %}
                </Items>
              </QueryStringCacheKeys>
            </ForwardedValues>
            <MinTTL>{{ cache_behavior_list.min_ttl }}</MinTTL>
            <DefaultTTL>{{ cache_behavior_list.default_ttl }}</DefaultTTL>
            <MaxTTL>{{ cache_behavior_list.max_ttl }}</MaxTTL>
          {% endfor %}
        </Items>
        {% endif %}
      </CacheBehaviors>
      <CustomErrorResponses>
        <Quantity>{{ distribution.distribution_config.custom_error_responses|length }}</Quantity>
        {% if distribution.distribution_config.custom_error_responses %}
        <Items>
          {% for response  in distribution.distribution_config.custom_error_responses %}
            <ErrorCode>{{ response.error_code }}</ErrorCode>
            <ResponsePagePath>{{ response.response_page_path }}</ResponsePagePath>
            <ResponseCode>{{ response.response_code }}</ResponseCode>
            <ErrorCachingMinTTL>{{ response.error_caching_min_ttl }}</ErrorCachingMinTTL>
          {% endfor %}
        </Items>
        {% endif %}
      </CustomErrorResponses>
      <Comment>{{ distribution.distribution_config.comment }}</Comment>
      <Logging>
        <Enabled>{{ distribution.distribution_config.logging.enabled }}</Enabled>
        <IncludeCookies>{{ distribution.distribution_config.logging.include_cookies }}</IncludeCookies>
        <Bucket>{{ distribution.distribution_config.logging.bucket }}</Bucket>
        <Prefix>{{ distribution.distribution_config.logging.prefix }}</Prefix>
      </Logging>
      <PriceClass>{{ distribution.distribution_config.price_class }}</PriceClass>
      <Enabled>{{ distribution.distribution_config.enabled }}</Enabled>
      <ViewerCertificate>
        <CloudFrontDefaultCertificate>{{ 'true' if distribution.distribution_config.viewer_certificate.cloud_front_default_certificate else 'false' }}</CloudFrontDefaultCertificate>
        <IAMCertificateId>{{ distribution.distribution_config.viewer_certificate.iam_certificate_id }}</IAMCertificateId>
        <ACMCertificateArn>{{ distribution.distribution_config.viewer_certificate.acm_certificate_arn }}</ACMCertificateArn>
        <SSLSupportMethod>{{ SSLSupportMethod }}</SSLSupportMethod>
        <MinimumProtocolVersion>{{ distribution.distribution_config.viewer_certificate.min_protocol_version }}</MinimumProtocolVersion>
        <Certificate>{{ distribution.distribution_config.viewer_certificate.certificate }}</Certificate>
        <CertificateSource>{{ distribution.distribution_config.viewer_certificate.certificate_source }}</CertificateSource>
      </ViewerCertificate>
      <Restrictions>
        <GeoRestriction>
          <RestrictionType>{{ distribution.distribution_config.geo_restriction_type }}</RestrictionType>
          <Quantity>{{ distribution.distribution_config.geo_restrictions|length }}</Quantity>
          {% if distribution.distribution_config.geo_restrictions %}
          <Items>
            {% for location  in distribution.distribution_config.geo_restrictions %}
              <Location>{{ location }}</Location>
            {% endfor %}
          </Items>
          {% endif %}
        </GeoRestriction>
      </Restrictions>
      <WebACLId>{{ distribution.distribution_config.web_acl_id }}</WebACLId>
      <HttpVersion>{{ distribution.distribution_config.http_version }}</HttpVersion>
      <IsIPV6Enabled>{{ 'true' if distribution.distribution_config.is_ipv6_enabled else 'false' }}</IsIPV6Enabled>
"""


DISTRIBUTION_TEMPLATE = (
    DIST_META_TEMPLATE
    + """
    <ActiveTrustedSigners>
      <Enabled>{{ distribution.active_trusted_signers.enabled }}</Enabled>
      <Quantity>{{ distribution.active_trusted_signers.quantity }}</Quantity>
      <Items>
        {% for signer  in distribution.active_trusted_signers.signers %}
          <AwsAccountNumber>{{ signer.aws_account_number }}</AwsAccountNumber>
          <KeyPairIds>
            <Quantity>{{ signer.key_pair_ids.quantity }}</Quantity>
            <Items>
              {% for key_pair_id_list  in signer.key_pair_ids.KeyPairIdList %}
                <KeyPairId>{{ key_pair_id_list.key_pair_id }}</KeyPairId>
              {% endfor %}
            </Items>
          </KeyPairIds>
        {% endfor %}
      </Items>
    </ActiveTrustedSigners>
    <ActiveTrustedKeyGroups>
      <Enabled>{{ distribution.active_trusted_key_groups.enabled }}</Enabled>
      <Quantity>{{ distribution.active_trusted_key_groups.quantity }}</Quantity>
      <Items>
        {% for kg_key_pair_id  in distribution.active_trusted_key_groups.kg_key_pair_ids %}
          <KeyGroupId>{{ kg_key_pair_id.key_group_id }}</KeyGroupId>
          <KeyPairIds>
            <Quantity>{{ kg_key_pair_id.key_pair_ids.quantity }}</Quantity>
            <Items>
              {% for key_pair_id_list  in kg_key_pair_ids_list.key_pair_ids.KeyPairIdList %}
                <KeyPairId>{{ key_pair_id_list.key_pair_id }}</KeyPairId>
              {% endfor %}
            </Items>
          </KeyPairIds>
        {% endfor %}
      </Items>
    </ActiveTrustedKeyGroups>
    <DistributionConfig>
      """
    + DIST_CONFIG_TEMPLATE
    + """
    </DistributionConfig>
    <AliasICPRecordals>
      {% for a  in distribution.alias_icp_recordals %}
        <CNAME>{{ a.cname }}</CNAME>
        <ICPRecordalStatus>{{ a.status }}</ICPRecordalStatus>
      {% endfor %}
    </AliasICPRecordals>"""
)

CREATE_DISTRIBUTION_TEMPLATE = (
    """<?xml version="1.0"?>
  <CreateDistributionResult xmlns="{{ xmlns }}">
"""
    + DISTRIBUTION_TEMPLATE
    + """
  </CreateDistributionResult>
"""
)

GET_DISTRIBUTION_TEMPLATE = (
    """<?xml version="1.0"?>
  <Distribution xmlns="{{ xmlns }}">
"""
    + DISTRIBUTION_TEMPLATE
    + """
  </Distribution>
"""
)


LIST_TEMPLATE = (
    """<?xml version="1.0"?>
<DistributionList xmlns="http://cloudfront.amazonaws.com/doc/2020-05-31/">
  <Marker></Marker>
  <MaxItems>100</MaxItems>
  <IsTruncated>false</IsTruncated>
  <Quantity>{{ distributions|length }}</Quantity>
  {% if distributions %}
  <Items>
      {% for distribution in distributions %}
      <DistributionSummary>
      """
    + DIST_META_TEMPLATE
    + """
      """
    + DIST_CONFIG_TEMPLATE
    + """
      </DistributionSummary>
      {% endfor %}
  </Items>
  {% endif %}
</DistributionList>"""
)

UPDATE_DISTRIBUTION_TEMPLATE = (
    """<?xml version="1.0"?>
  <Distribution xmlns="{{ xmlns }}">
"""
    + DISTRIBUTION_TEMPLATE
    + """
  </Distribution>
"""
)
