package main

import (
	"context"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/cloudwatchlogs"
)

func TestDescribeQueries(t *testing.T) {
	cfg, err := config.LoadDefaultConfig(
		context.Background(),
		config.WithBaseEndpoint("http://localhost:5000"),
		config.WithRegion("us-east-1"),
		config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider("EXAMPLE", "EXAMPLE", "EXAMPLE")),
		config.WithClientLogMode(aws.LogRequestWithBody|aws.LogResponseWithBody),
	)
	if err != nil {
		t.Fatal(err)
	}

	logsClient := cloudwatchlogs.NewFromConfig(cfg)
	ctx := context.Background()

	logGroupName := aws.String("go-describe-queries")
	_, err = logsClient.CreateLogGroup(ctx, &cloudwatchlogs.CreateLogGroupInput{
		LogGroupName: logGroupName,
	})
	if err != nil {
		t.Fatal(err)
	}

	now := time.Now().Unix()
	_, err = logsClient.StartQuery(ctx, &cloudwatchlogs.StartQueryInput{
		LogGroupName: logGroupName,
		StartTime:    aws.Int64(now - 60),
		EndTime:      aws.Int64(now),
		QueryString:  aws.String("fields @message"),
	})
	if err != nil {
		t.Fatal(err)
	}

	// The SDK fails to deserialize createTime unless it is an integer
	output, err := logsClient.DescribeQueries(ctx, &cloudwatchlogs.DescribeQueriesInput{
		LogGroupName: logGroupName,
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(output.Queries) != 1 {
		t.Fatalf("expected 1 query, got %d", len(output.Queries))
	}
	if aws.ToInt64(output.Queries[0].CreateTime) == 0 {
		t.Fatal("expected createTime to be set")
	}
}
