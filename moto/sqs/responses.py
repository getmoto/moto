from urlparse import parse_qs

from jinja2 import Template

from moto.core.utils import headers_to_dict, camelcase_to_underscores, method_names_from_class
from .models import sqs_backend


class BaseResponse(object):
    def dispatch(self, uri, body, headers):
        if body:
            querystring = parse_qs(body)
        else:
            querystring = headers_to_dict(headers)

        self.path = uri.path
        self.querystring = querystring

        action = querystring['Action'][0]
        action = camelcase_to_underscores(action)

        method_names = method_names_from_class(self.__class__)
        if action in method_names:
            method = getattr(self, action)
            return method()
        raise NotImplementedError("The {} action has not been implemented".format(action))


class QueuesResponse(BaseResponse):

    def create_queue(self):
        visibility_timeout = None
        if 'Attribute.1.Name' in self.querystring and self.querystring.get('Attribute.1.Name')[0] == 'VisibilityTimeout':
            visibility_timeout = self.querystring.get("Attribute.1.Value")[0]

        queue_name = self.querystring.get("QueueName")[0]
        queue = sqs_backend.create_queue(queue_name, visibility_timeout=visibility_timeout)
        template = Template(CREATE_QUEUE_RESPONSE)
        return template.render(queue=queue)

    def list_queues(self):
        queues = sqs_backend.list_queues()
        template = Template(LIST_QUEUES_RESPONSE)
        return template.render(queues=queues)


class QueueResponse(BaseResponse):
    def get_queue_attributes(self):
        queue_name = self.path.split("/")[-1]
        queue = sqs_backend.get_queue(queue_name)
        template = Template(GET_QUEUE_ATTRIBUTES_RESPONSE)
        return template.render(queue=queue)

    def delete_queue(self):
        queue_name = self.path.split("/")[-1]
        queue = sqs_backend.delete_queue(queue_name)
        if not queue:
            return "A queue with name {} does not exist".format(queue_name), dict(status=404)
        template = Template(DELETE_QUEUE_RESPONSE)
        return template.render(queue=queue)



CREATE_QUEUE_RESPONSE = """<CreateQueueResponse>
    <CreateQueueResult>
        <QueueUrl>http://sqs.us-east-1.amazonaws.com/123456789012/{{ queue.name }}</QueueUrl>
        <VisibilityTimeout>{{ queue.visibility_timeout }}</VisibilityTimeout>
    </CreateQueueResult>
    <ResponseMetadata>
        <RequestId>
            7a62c49f-347e-4fc4-9331-6e8e7a96aa73
        </RequestId>
    </ResponseMetadata>
</CreateQueueResponse>"""

LIST_QUEUES_RESPONSE = """<ListQueuesResponse>
    <ListQueuesResult>
        {% for queue in queues %}
            <QueueUrl>http://sqs.us-east-1.amazonaws.com/123456789012/{{ queue.name }}</QueueUrl>
            <VisibilityTimeout>{{ queue.visibility_timeout }}</VisibilityTimeout>
        {% endfor %}
    </ListQueuesResult>
    <ResponseMetadata>
        <RequestId>
            725275ae-0b9b-4762-b238-436d7c65a1ac
        </RequestId>
    </ResponseMetadata>
</ListQueuesResponse>"""

DELETE_QUEUE_RESPONSE = """<DeleteQueueResponse>
    <ResponseMetadata>
        <RequestId>
            6fde8d1e-52cd-4581-8cd9-c512f4c64223
        </RequestId>
    </ResponseMetadata>
</DeleteQueueResponse>"""

GET_QUEUE_ATTRIBUTES_RESPONSE = """<GetQueueAttributesResponse>
  <GetQueueAttributesResult>
    {% for key, value in queue.attributes.items() %}
        <Attribute>
          <Name>{{ key }}</Name>
          <Value>{{ value }}</Value>
        </Attribute>
    {% endfor %}
  </GetQueueAttributesResult>
  <ResponseMetadata>
    <RequestId>1ea71be5-b5a2-4f9d-b85a-945d8d08cd0b</RequestId>
  </ResponseMetadata>
</GetQueueAttributesResponse>"""