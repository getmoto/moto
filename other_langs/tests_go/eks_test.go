package main

import (
	"context"
	"testing"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/eks"
	"github.com/aws/aws-sdk-go-v2/service/eks/types"
)

func TestClusterCreate(t *testing.T) {
	cfg, err := config.LoadDefaultConfig(
		context.Background(),
		config.WithBaseEndpoint("http://localhost:5000"),
		config.WithRegion("us-east-1"),
		config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider("EXAMPLE", "EXAMPLE", "EXAMPLE")),
		config.WithClientLogMode(aws.LogRequestWithBody|aws.LogResponseWithBody),
	)

	eksClient := eks.NewFromConfig(cfg)

	input := &eks.CreateClusterInput{
		Name: aws.String("target-cluster"),
		ResourcesVpcConfig: &types.VpcConfigRequest{
			SubnetIds: []string{},
		},
		RoleArn: aws.String("arn:aws:iam::123456789012:role/eks-cluster-role"),
	}

	ctx := context.Background()
	_, err = eksClient.CreateCluster(ctx, input)
	if err != nil {
		panic(err)
	}
}
