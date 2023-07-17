using FluentAssertions;

// To interact with Amazon EBS
using Amazon.EBS;
using Amazon.EBS.Model;

using System.Security.Cryptography;


public class EbsSnashotTest
{
    [Fact]
    public async Task TestSnapshotCreation()
    {

        AmazonEBSConfig config = new AmazonEBSConfig()
        {
            ServiceURL = "http://localhost:5000",
        };

        AmazonEBSClient ebsClient = new AmazonEBSClient(config);

        // https://docs.aws.amazon.com/ebs/latest/APIReference/API_StartSnapshot.html
        var startSnapshotRequest = new StartSnapshotRequest { VolumeSize = 1 };
        var startSnapshotResponse = await ebsClient.StartSnapshotAsync(startSnapshotRequest);
        startSnapshotResponse.Status.Should().Be("pending");    

        // https://docs.aws.amazon.com/ebs/latest/APIReference/API_PutSnapshotBlock.html
        var blockData = new byte[] { 0x01, 0x02, 0x03, 0x04 };
        Stream blockDataStream = new MemoryStream(blockData);
        SHA256Managed sha256hasher = new SHA256Managed();
        byte[] sha256Hash = sha256hasher.ComputeHash(blockDataStream);
        var sha256checksum = Convert.ToBase64String(sha256Hash);
        var putSnapshotBlockRequest = new PutSnapshotBlockRequest
        {
            BlockIndex = 0,
            Checksum = sha256checksum,
            ChecksumAlgorithm = "SHA256",
            DataLength = blockData.Length,
            SnapshotId = startSnapshotResponse.SnapshotId,
            BlockData = blockDataStream
        };
        var putSnapshotBlockResponse = await ebsClient.PutSnapshotBlockAsync(putSnapshotBlockRequest);
        putSnapshotBlockResponse.Checksum.Should().Be(sha256checksum);
        putSnapshotBlockResponse.ChecksumAlgorithm.Should().Be("SHA256");

        https://docs.aws.amazon.com/ebs/latest/APIReference/API_CompleteSnapshot.html
        var completeSnapshotRequest = new CompleteSnapshotRequest
        {
            ChangedBlocksCount = 1,
            SnapshotId = startSnapshotResponse.SnapshotId
        };
        var completeSnapshotResponse = await ebsClient.CompleteSnapshotAsync(completeSnapshotRequest);
        completeSnapshotResponse.Status.Should().Be("completed");
    }
}
