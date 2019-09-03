from moto.core.responses import BaseResponse
from .models import eb_backends

EB_CREATE_APPLICATION = """
<CreateApplicationResponse xmlns="http://elasticbeanstalk.amazonaws.com/docs/2010-12-01/">
  <CreateApplicationResult>
    <Application>
      <ConfigurationTemplates/>
      <DateCreated>2019-09-03T13:08:29.049Z</DateCreated>
      <ResourceLifecycleConfig>
        <VersionLifecycleConfig>
          <MaxAgeRule>
            <DeleteSourceFromS3>false</DeleteSourceFromS3>
            <MaxAgeInDays>180</MaxAgeInDays>
            <Enabled>false</Enabled>
          </MaxAgeRule>
          <MaxCountRule>
            <DeleteSourceFromS3>false</DeleteSourceFromS3>
            <MaxCount>200</MaxCount>
            <Enabled>false</Enabled>
          </MaxCountRule>
        </VersionLifecycleConfig>
      </ResourceLifecycleConfig>
      <ApplicationArn>arn:aws:elasticbeanstalk:{{ region_name }}:111122223333:application/{{ application_name }}</ApplicationArn>
      <ApplicationName>{{ application.application_name }}</ApplicationName>
      <DateUpdated>2019-09-03T13:08:29.049Z</DateUpdated>
    </Application>
  </CreateApplicationResult>
  <ResponseMetadata>
    <RequestId>1b6173c8-13aa-4b0a-99e9-eb36a1fb2778</RequestId>
  </ResponseMetadata>
</CreateApplicationResponse>
"""


EB_DESCRIBE_APPLICATIONS = """
<DescribeApplicationsResponse xmlns="http://elasticbeanstalk.amazonaws.com/docs/2010-12-01/">
  <DescribeApplicationsResult>
    <Applications>
      {% for application in applications %}
      <member>
        <ConfigurationTemplates/>
        <DateCreated>2019-09-03T13:08:29.049Z</DateCreated>
        <ResourceLifecycleConfig>
          <VersionLifecycleConfig>
            <MaxAgeRule>
              <MaxAgeInDays>180</MaxAgeInDays>
              <DeleteSourceFromS3>false</DeleteSourceFromS3>
              <Enabled>false</Enabled>
            </MaxAgeRule>
            <MaxCountRule>
              <DeleteSourceFromS3>false</DeleteSourceFromS3>
              <MaxCount>200</MaxCount>
              <Enabled>false</Enabled>
            </MaxCountRule>
          </VersionLifecycleConfig>
        </ResourceLifecycleConfig>
        <ApplicationArn>arn:aws:elasticbeanstalk:{{ region_name }}:387323646340:application/{{ application.name }}</ApplicationArn>
        <ApplicationName>{{ application.application_name }}</ApplicationName>
        <DateUpdated>2019-09-03T13:08:29.049Z</DateUpdated>
      </member>
      {% endfor %}
    </Applications>
  </DescribeApplicationsResult>
  <ResponseMetadata>
    <RequestId>015a05eb-282e-4b76-bd18-663fdfaf42e4</RequestId>
  </ResponseMetadata>
</DescribeApplicationsResponse>
"""


class EBResponse(BaseResponse):
    @property
    def backend(self):
        return eb_backends[self.region]

    def create_application(self):
        app = self.backend.create_application(
            application_name=self._get_param('ApplicationName'),
        )

        template = self.response_template(EB_CREATE_APPLICATION)
        return template.render(
            region_name=self.backend.region,
            application=app,
        )

    def describe_applications(self):
        template = self.response_template(EB_DESCRIBE_APPLICATIONS)
        return template.render(
            applications=self.backend.applications.values(),
        )
