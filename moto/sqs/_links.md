https://github.com/boto/botocore/pull/3054
https://github.com/localstack/localstack/pull/9611
https://github.com/localstack/localstack/pull/9710
https://smithy.io/2.0/aws/protocols/aws-query-protocol.html#aws-protocols-awsquerycompatible-trait
https://github.com/boto/botocore/pull/3515

JSON:
botocore.errorfactory.QueueDoesNotExist: An error occurred (AWS.SimpleQueueService.NonExistentQueue) when calling the GetQueueUrl operation: The specified queue does not exist.
Query:
botocore.errorfactory.QueueDoesNotExist: An error occurred (AWS.SimpleQueueService.NonExistentQueue) when calling the GetQueueUrl operation: The specified queue does not exist for this wsdl version.

Check out all the customizations that localstack did for SQS:
*explicit quoting of quotes and linebreaks in XML responses
*error code translations 


2025-10-07:
I got things working using current botocore as well as the last botocore release that 
had the Query specification.  But I'm now realizing that of course this works for the 
decorator tests, but it's not going to work in server mode when Moto is using the latest 
botocore spec and the client is using the old Query spec.
So... I need to modify the SQS Tests workflow again to spin up Moto in server mode and 
then install the old botocore version for the tests to run under. 
Should get *lots* of failures, since I think at a minimum all the of XML responses 
require a resultwrapper that won't be in the spec that Moto loads.