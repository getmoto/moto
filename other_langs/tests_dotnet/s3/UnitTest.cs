using FluentAssertions;
using System.Net;

// To interact with Amazon S3.
using Amazon.S3;
using Amazon.S3.Model;

public class UnitTest1
{

    [Fact]
    public async Task TestListBuckets()
    {

        AmazonS3Config config = new AmazonS3Config()
        {
            ServiceURL = "http://localhost:5000",
        };

        AmazonS3Client s3Client = new AmazonS3Client(config);

        var initial_list = await s3Client.ListBucketsAsync();
        initial_list.Buckets.Count.Should().Be(0);

        var putBucketRequest = new PutBucketRequest
        {
            BucketName = "MyFirstBucket",
            UseClientRegion = true
        };
        await s3Client.PutBucketAsync(putBucketRequest);

        var listResponse = await s3Client.ListBucketsAsync();
        listResponse.Buckets.Count.Should().Be(1);
    }
}