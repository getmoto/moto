package moto.tests;

import org.junit.Test;

import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.DeleteBucketRequest;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.HeadBucketRequest;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import moto.tests.DependencyFactory;

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
        PutObjectRequest put_request = PutObjectRequest.builder().bucket(bucketName).key(keyName).build();
        s3Client.putObject(put_request, RequestBody.fromString("Testing with the {sdk-java}"));
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
