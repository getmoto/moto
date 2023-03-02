package moto.tests;

import software.amazon.awssdk.http.SdkHttpClient;
import software.amazon.awssdk.http.SdkHttpConfigurationOption;
import software.amazon.awssdk.http.apache.ApacheHttpClient;
import software.amazon.awssdk.http.urlconnection.UrlConnectionHttpClient;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.utils.AttributeMap;

import java.net.URI;
import java.time.Duration;

/**
 * The module containing all dependencies required by the {@link Handler}.
 */
public class DependencyFactory {

    private static final URI MOTO_URI = URI.create("http://localhost:5000");

    private DependencyFactory() {}

    /**
     * @return an instance of S3Client
     */
    public static S3Client s3Client() {
        return S3Client.builder()
                .region(Region.US_EAST_1)
                .httpClientBuilder(ApacheHttpClient.builder())
                .endpointOverride(MOTO_URI)
                .build();
    }

    public static DynamoDbClient dynamoClient() {
        final AttributeMap attributeMap = AttributeMap.builder()
                .put(SdkHttpConfigurationOption.TRUST_ALL_CERTIFICATES, true)
                .build();
        // Not in use at the moment, but useful for testing
        SdkHttpClient proxy_client = UrlConnectionHttpClient.builder()
                .socketTimeout(Duration.ofMinutes(1))
                .proxyConfiguration(proxy -> proxy.endpoint(URI.create("http://localhost:8080")))
                .buildWithDefaults(attributeMap);
        return DynamoDbClient.builder()
                .region(Region.US_EAST_1)
                // .httpClient(client)
                .httpClientBuilder(ApacheHttpClient.builder())
                .endpointOverride(MOTO_URI)
                .build();
    }
}