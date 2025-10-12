using FluentAssertions;
using System.Net;

// To interact with Amazon S3.
using Amazon.SQS;
using Amazon.SQS.Model;

public class UnitTest1
{

    [Fact]
    public async Task TestCreateQueue()
    {

        // Create an SQS client connected to the local moto server
        var sqsClient = new AmazonSQSClient(
            new AmazonSQSConfig
            {
                // Use the local Moto server URL
                ServiceURL = "http://127.0.0.1:5000",

            });

        // Create the queue and get the response
        var createQueueResponse = await CreateQueueAsync(sqsClient);
        createQueueResponse.QueueUrl.Should().Be("http://127.0.0.1:5000/123456789012/MyQueue");
    }

    private static async Task<CreateQueueResponse> CreateQueueAsync(AmazonSQSClient sqsClient)
    {
        var createQueueRequest = new CreateQueueRequest
        {
            QueueName = "MyQueue"
        };

        return await sqsClient.CreateQueueAsync(createQueueRequest);
    }

}