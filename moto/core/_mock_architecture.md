Introduction
-------------

Aim: to document how Moto's mocks work, and provide some architectural background info.

`Moto` is responsible for mocking the AWS API, and it does this by providing two key capabilities:


## Mock requests coming from botocore

Requests coming from botocore are mocked by the `BotocoreStubber`. This class is responsible for two main functions:
 - Inspect the incoming request to determine which method should handle this request
 - Execute the method and process the result as appropriate

`botocore` has an event handling system used to enhance/augment requests that were made. Using this approach, `Moto` automatically registers the `BotocoreStubber` as an event handler that is invoked for every `before_send`-event. 

This event is one of the last ones to fire before the actual HTTP request is made, which means that `botocore` is still responsible for any client-side validation.

### Usage of the event handling system

The intention of the `botocore` event system is to register event handlers with a specific botocore `Session`. That approach has multiple problems:
 - Moto can enrich the default session, but has no control (or knowledge) of any Session's created by the end-user.
 - `botocore` copies event handlers for some reason, which means that
   - the same request is sometimes processed by multiple `BotocoreStubber`'s, resulting in duplicate resources
   - `Moto` has no control over all event handlers, so they can't be enabled/disabled - resulting in the mock still being active after the `Moto` decorator ends

That's why `Moto` uses a single global instance of the `BotocoreStubber`, which is enabled and disabled for the duration of a `mock_aws`-decorator. Note that if the end-user nests multiple `mock_aws`-decorators, `Moto` will only disable the mock after the last decorator finishes.

## Mock requests coming from the `requests`-module

Users can manually invoke the AWS API using the `requests`-module. That means that `Moto` needs to intercept all these requests and determine the result on the fly.

Because the `BotocoreStubber` already contains all the logic necessary to parse incoming HTTP requests to AWS, we re-use this logic for requests intercepted by from the `responses` module.

### Supported requests

`Moto` maintains a list of URL's for each supported AWS service. This list can be seen in `moto/backend_index.py`.

If a `botocore` request comes through, `Moto` will cycle through this list to see whether the request is supported. If it is not supported, it will return a `404 NotYetImplemented` response.

The `requests`-module achieves the same result, but using a different approach. It has specific callbacks for every supported URL, and a separate `NotYetImplemented`-callback that catches every (unhandled) request to `*.amazonaws.com`. 