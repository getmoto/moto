package moto.tests;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;
import software.amazon.awssdk.services.ses.SesClient;
import software.amazon.awssdk.services.ses.model.Body;
import software.amazon.awssdk.services.ses.model.Content;
import software.amazon.awssdk.services.ses.model.Destination;
import software.amazon.awssdk.services.ses.model.Message;
import software.amazon.awssdk.services.ses.model.SendEmailRequest;
import software.amazon.awssdk.services.ses.model.VerifyEmailAddressRequest;
import software.amazon.awssdk.services.ses.model.GetSendStatisticsResponse;
import software.amazon.awssdk.services.ses.model.SesException;

class SESTest {

    @Test
    void testUnverifiedEmail() {
        SesClient sesClient = DependencyFactory.sesClient();

        Message message = Message
                .builder()
                .subject(Content.builder().charset("UTF-8").data("subject").build())
                .body(Body.builder().text(Content.builder().charset("UTF-8").data("body").build()).build())
                .build();

        SendEmailRequest request = SendEmailRequest
                .builder()
                .source("noreply@thedomain.com")
                .destination(Destination.builder().toAddresses(List.of("one@one.com")).build())
                .message(message)
                .build();

        try {
            System.out.println("Attempting to send an email...");
            sesClient.sendEmail(request);

        } catch (SesException e) {
            assertEquals("Email address not verified noreply@thedomain.com", e.awsErrorDetails().errorMessage());
        }
    }

    @Test
    void testGetSendStatistics() {
        SesClient sesClient = DependencyFactory.sesClient();

        VerifyEmailAddressRequest verifyEmailAddressRequest = VerifyEmailAddressRequest.builder().emailAddress("noreply@thedomain.com").build();
        sesClient.verifyEmailAddress(verifyEmailAddressRequest);

        Message message = Message
                .builder()
                .subject(Content.builder().charset("UTF-8").data("subject").build())
                .body(Body.builder().text(Content.builder().charset("UTF-8").data("body").build()).build())
                .build();

        SendEmailRequest request = SendEmailRequest
                .builder()
                .source("noreply@thedomain.com")
                .destination(Destination.builder().toAddresses(List.of("one@one.com")).build())
                .message(message)
                .build();

        GetSendStatisticsResponse statisticsBefore = sesClient.getSendStatistics();
        Long prev = statisticsBefore.sendDataPoints().get(0).deliveryAttempts().longValue();

        sesClient.sendEmail(request);

        GetSendStatisticsResponse statisticsAfter = sesClient.getSendStatistics();
        Long after = statisticsAfter.sendDataPoints().get(0).deliveryAttempts().longValue();

        assertTrue(after > prev, "Delivery attempts should increase");
    }
}
