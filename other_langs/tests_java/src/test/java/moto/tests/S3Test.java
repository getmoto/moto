package moto.tests;

import org.junit.jupiter.api.Test;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.ResponseBytes;
import software.amazon.awssdk.core.async.AsyncRequestBody;
import software.amazon.awssdk.core.sync.ResponseTransformer;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3AsyncClient;
import software.amazon.awssdk.services.s3.model.*;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.transfer.s3.S3TransferManager;

import java.io.ByteArrayInputStream;
import java.net.URI;
import java.util.concurrent.Executors;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Unit test for simple App.
 */
class S3Test
{

    @Test
    void put_object_string() {
        String bucketName = "bucket" + System.currentTimeMillis();
        String keyName = "mykey";
        S3Client s3Client = DependencyFactory.s3Client();

        // Create Bucket
        s3Client.createBucket(CreateBucketRequest
                    .builder()
                    .bucket(bucketName)
                    .build());
        s3Client.waiter().waitUntilBucketExists(HeadBucketRequest.builder()
                    .bucket(bucketName)
                    .build());


        // Upload Object with static data
        String initialString = "Testing with the {sdk-java}";
        PutObjectRequest put_request = PutObjectRequest.builder().bucket(bucketName).key(keyName).build();
        s3Client.putObject(put_request, RequestBody.fromString(initialString));

        GetObjectRequest objectRequest = GetObjectRequest
                .builder()
                .key(keyName)
                .bucket(bucketName)
                .build();

        ResponseBytes<GetObjectResponse> objectBytes = s3Client.getObject(objectRequest, ResponseTransformer.toBytes());
        String receivedString = objectBytes.asUtf8String();

        assertEquals(initialString, receivedString);
    }

    @Test
    void create_and_delete_bucket() {
        String bucketName = "bucket" + System.currentTimeMillis();
        S3Client s3Client = DependencyFactory.s3Client();

        // Create Bucket
        s3Client.createBucket(CreateBucketRequest
                    .builder()
                    .bucket(bucketName)
                    .build());
        s3Client.waiter().waitUntilBucketExists(HeadBucketRequest.builder()
                    .bucket(bucketName)
                    .build());

        // Delete Bucket
        DeleteBucketRequest deleteBucketRequest = DeleteBucketRequest.builder().bucket(bucketName).build();
        s3Client.deleteBucket(deleteBucketRequest);
    }

    @Test
    void upload_file_using_transfer_manager() {
        var inputStream = new ByteArrayInputStream("test-content".getBytes());
        var client = S3AsyncClient.crtBuilder()
                .forcePathStyle(true)
                .endpointOverride(URI.create("http://localhost:5000"))
                .region(Region.of("eu-central-1"))
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create("test", "test")))
                .build();

        client.createBucket(builder -> builder.bucket("test-bucket"));

        var transferManager = S3TransferManager.builder()
                .s3Client(client)
                .build();
        var executor = Executors.newSingleThreadExecutor();
        var body = AsyncRequestBody.fromInputStream(inputStream, null, executor);

        var upload = transferManager.upload(builder -> builder
                .requestBody(body)
                .putObjectRequest(req -> req.bucket("test-bucket").key("test-key"))
                .build());

        upload.completionFuture().join();
        executor.shutdown();
        transferManager.close();
        client.close();
    }
}
