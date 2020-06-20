from __future__ import unicode_literals
from moto.core.responses import BaseResponse

from moto.core.utils import (
    amz_crc32,
    amzn_request_id,
)
from .models import applicationautoscaling_backends


class ApplicationAutoScalingResponse(BaseResponse):

    @property
    def applicationautoscaling_backend(self):
        return applicationautoscaling_backends[self.region]

    @amz_crc32
    @amzn_request_id
    def describe_scalable_targets(self):
        service_namespace = self._get_param("ServiceNamespace")
        resource_ids = self._get_multi_param("ResourceIds")
        scalable_dimension = self._get_param("ScalableDimension")
        max_results = self._get_int_param("MaxResults", 50)
        all_scalable_targets = self.applicationautoscaling_backend.describe_scalable_targets(
            service_namespace, resource_ids, scalable_dimension
        )
        marker = self._get_param("NextToken")
        start = all_scalable_targets.index(marker) + 1 if marker else 0
        template = self.response_template(DESCRIBE_SCALABLE_TARGETS_TEMPLATE)
        next_token = None
        scalable_targets_resp = all_scalable_targets[start: start + max_results]
        if len(all_scalable_targets) > start + max_results:
            next_token = scalable_targets_resp[-1].name
        return template.render(scalable_targets=scalable_targets_resp, next_token=next_token)


DESCRIBE_SCALABLE_TARGETS_TEMPLATE = """<DescribeScalableTargetsResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
    <DescribeScalableTargetsResult>
    <ScalableTargets>
    {% for scalable_target in scalable_targets %}
        <ScalableTarget>
            <CreationTime>{{ scalable_target.creation_time }}</CreationTime>
            <MaxCapacity>{{ scalable_target.max_capacity }}</MaxCapacity>
            <MinCapacity>{{ scalable_target.min_capacity }}</MinCapacity>
            <ResourceId>{{ scalable_target.resource_id }}</ResourceId>
            <RoleARN>{{ scalable_target.role_arn }}</RoleARN>
            <ScalableDimension>{{ scalable_target.scalable_dimension }}</ScalableDimension>
            <ServiceNamespace>{{ scalable_target.service_namespace }}</ServiceNamespace>
            <SuspendedState>
                <DynamicScalingInSuspended>{{ scalable_target.dynamic_scaling_in_suspended }}</DynamicScalingInSuspended>
                <DynamicScalingOutSuspended>{{ scalable_target.dynamic_scaling_out_suspended }}</DynamicScalingOutSuspended>
                <ScheduledScalingSuspended>{{ scalable_target.scheduled_scaling_suspended }}</ScheduledScalingSuspended>
            </SuspendedState>
        <ScalableTarget>
    {% endfor %}
    </ScalableTargets>
    {% if next_token %}
    <NextToken>{{ next_token }}</NextToken>
    {% endif %}
    </DescribeScalableTargetsResult>
    <ResponseMetadata>
       <RequestId>7c6e177f-f082-11e1-ac58-3714bEXAMPLE</RequestId>
    </ResponseMetadata>
</DescribeScalableTargetsResponse>"""
