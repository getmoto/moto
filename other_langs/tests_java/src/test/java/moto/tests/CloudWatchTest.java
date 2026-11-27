package moto.tests;

import static moto.tests.DependencyFactory.cloudWatchClient;
import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;
import software.amazon.awssdk.services.cloudwatch.CloudWatchClient;
import software.amazon.awssdk.services.cloudwatch.model.*;
import software.amazon.awssdk.services.cloudwatch.paginators.ListMetricsIterable;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class CloudWatchTest {

    @Test
    void testAssociateSoftwareToken() {
        CloudWatchClient client = cloudWatchClient();

        String myMetric = randomString();

        String myNamespace = randomString();

        List<MetricDatum> points = new ArrayList<>();
        points.add(MetricDatum.builder()
                .metricName(myMetric)          // Name of your metric
                .timestamp(Instant.now())              // When the metric was recorded
                .value(42.0)                           // Metric value
                .unit(StandardUnit.COUNT)              // Unit type (e.g., Count, Seconds, Bytes)
                .build());
        points.add(MetricDatum.builder()
                .metricName(myMetric)          // Name of your metric
                .timestamp(Instant.now())              // When the metric was recorded
                .dimensions(Dimension.builder().name("dimension1").value("val").build())
                .value(7.0)                           // Metric value
                .unit(StandardUnit.BYTES)              // Unit type (e.g., Count, Seconds, Bytes)
                .build());

        final PutMetricDataRequest putRequest = PutMetricDataRequest.builder().namespace(myNamespace)
                .metricData(points).build();
        client.putMetricData(putRequest);

        final ListMetricsRequest listRequest = ListMetricsRequest.builder().namespace(myNamespace).build();

        ListMetricsIterable responses = client.listMetricsPaginator(listRequest);

        for (Metric metric : responses.metrics()) {
            assertEquals(myMetric, metric.metricName());
        }
    }

    String randomString() {
        int leftLimit = 48; // numeral '0'
        int rightLimit = 122; // letter 'z'
        int targetLength = 10;
        Random random = new Random();

        return random.ints(leftLimit, rightLimit + 1)
                .filter(i -> (i <= 57 || i >= 65) && (i <= 90 || i >= 97))
                .limit(targetLength)
                .collect(StringBuilder::new, StringBuilder::appendCodePoint, StringBuilder::append)
                .toString();
    }
}
