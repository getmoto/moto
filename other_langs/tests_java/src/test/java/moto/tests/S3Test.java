package moto.tests;

import org.junit.Test;

import software.amazon.awssdk.core.ResponseBytes;
import software.amazon.awssdk.core.sync.ResponseTransformer;
import software.amazon.awssdk.services.s3.model.*;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;

import static org.junit.Assert.assertEquals;

/**
 * Unit test for simple App.
 */
public class S3Test
{

    @Test
    public void put_object_string() {
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
    public void create_and_delete_bucket() {
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
}
