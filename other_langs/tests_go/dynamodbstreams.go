package main

import (
	"context"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/aws/aws-sdk-go-v2/service/dynamodbstreams"
)

const (
	Endpoint  = "http://localhost:5000"
	Region    = "us-east-1"
	TableName = "TableWithStreamEnabled"
)

func DescribeStream() *dynamodbstreams.DescribeStreamOutput {

	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		panic(err)
	}

	ddbClient := dynamodb.NewFromConfig(cfg, func(o *dynamodb.Options) {
		o.BaseEndpoint = aws.String(Endpoint)
		o.Region = Region
	})

	result, err := ddbClient.CreateTable(context.TODO(), &dynamodb.CreateTableInput{
		TableName: aws.String(TableName),
		AttributeDefinitions: []types.AttributeDefinition{
			{
				AttributeName: aws.String("PK"),
				AttributeType: types.ScalarAttributeTypeS,
			},
			{
				AttributeName: aws.String("SK"),
				AttributeType: types.ScalarAttributeTypeS,
			},
		},
		KeySchema: []types.KeySchemaElement{
			{
				AttributeName: aws.String("PK"),
				KeyType:       types.KeyTypeHash,
			},
			{
				AttributeName: aws.String("SK"),
				KeyType:       types.KeyTypeRange,
			},
		},
		ProvisionedThroughput: &types.ProvisionedThroughput{
			ReadCapacityUnits:  aws.Int64(5),
			WriteCapacityUnits: aws.Int64(5),
		},
		StreamSpecification: &types.StreamSpecification{
			StreamEnabled:  aws.Bool(true),
			StreamViewType: "NEW_AND_OLD_IMAGES",
		},
	})

	if err != nil {
		panic(err)
	}

	streamArn := *result.TableDescription.LatestStreamArn
	ddbsClient := dynamodbstreams.NewFromConfig(cfg, func(o *dynamodbstreams.Options) {
		o.BaseEndpoint = aws.String(Endpoint)
		o.Region = Region
	})
	streamInfo, err := ddbsClient.DescribeStream(context.TODO(), &dynamodbstreams.DescribeStreamInput{
		StreamArn: aws.String(streamArn),
	})
	if err != nil {
		panic(err)
	}
	return streamInfo
}
