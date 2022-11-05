package com.amazonaws.examples

import com.amazonaws.client.builder.AwsClientBuilder
import com.amazonaws.regions.{Region, Regions}
import com.amazonaws.services.sqs.AmazonSQSClientBuilder

import scala.jdk.CollectionConverters._

object QueueTest extends App {
  val region = Region.getRegion(Regions.US_WEST_2).getName
  val serviceEndpoint = "http://localhost:5000"

  val amazonSqs =  AmazonSQSClientBuilder.standard()
    .withEndpointConfiguration(
      new AwsClientBuilder.EndpointConfiguration(serviceEndpoint, region))
    .build

  val queueName = "my-first-queue"
  amazonSqs.createQueue(queueName)

  val urls = amazonSqs.listQueues().getQueueUrls.asScala
  println("Listing queues")
  println(urls.map(url => s" - $url").mkString(System.lineSeparator))
  println()
}
