package main

import (
	"context"
	"errors"
	"fmt"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/cloudwatch"
	"github.com/aws/aws-sdk-go-v2/service/cloudwatch/types"
)

// The Go SDK uses the Smithy RPC v2 CBOR protocol for CloudWatch.
func newCloudWatchClient(t *testing.T) *cloudwatch.Client {
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
	return cloudwatch.NewFromConfig(cfg)
}

func TestCloudWatchMetricData(t *testing.T) {
	client := newCloudWatchClient(t)
	ctx := context.Background()

	// Unique per run, so the test can be repeated against the same server
	timestamp := time.Now().UTC().Truncate(time.Second)
	namespace := aws.String("go-cloudwatch-metric-data")
	metricName := aws.String(fmt.Sprintf("metric-%d", timestamp.Unix()))
	_, err := client.PutMetricData(ctx, &cloudwatch.PutMetricDataInput{
		Namespace: namespace,
		MetricData: []types.MetricDatum{
			{
				MetricName: metricName,
				Value:      aws.Float64(1.5),
				Timestamp:  aws.Time(timestamp),
				Unit:       types.StandardUnitSeconds,
				Dimensions: []types.Dimension{{Name: aws.String("name"), Value: aws.String("value")}},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	metrics, err := client.ListMetrics(ctx, &cloudwatch.ListMetricsInput{Namespace: namespace, MetricName: metricName})
	if err != nil {
		t.Fatal(err)
	}
	if len(metrics.Metrics) != 1 {
		t.Fatalf("expected 1 metric, got %d", len(metrics.Metrics))
	}
	if aws.ToString(metrics.Metrics[0].Dimensions[0].Value) != "value" {
		t.Fatalf("unexpected dimensions: %+v", metrics.Metrics[0].Dimensions)
	}

	data, err := client.GetMetricData(ctx, &cloudwatch.GetMetricDataInput{
		StartTime: aws.Time(timestamp.Add(-time.Minute)),
		EndTime:   aws.Time(timestamp.Add(time.Minute)),
		MetricDataQueries: []types.MetricDataQuery{
			{
				Id: aws.String("query"),
				MetricStat: &types.MetricStat{
					Metric: &types.Metric{
						Namespace:  namespace,
						MetricName: metricName,
						Dimensions: []types.Dimension{{Name: aws.String("name"), Value: aws.String("value")}},
					},
					Period: aws.Int32(60),
					Stat:   aws.String("Sum"),
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	result := data.MetricDataResults[0]
	if len(result.Values) != 1 || result.Values[0] != 1.5 {
		t.Fatalf("unexpected values: %v", result.Values)
	}
	if len(result.Timestamps) != 1 || result.Timestamps[0].IsZero() {
		t.Fatalf("unexpected timestamps: %v", result.Timestamps)
	}
}

func TestCloudWatchAlarms(t *testing.T) {
	client := newCloudWatchClient(t)
	ctx := context.Background()

	alarmName := aws.String("go-cloudwatch-alarm")
	_, err := client.PutMetricAlarm(ctx, &cloudwatch.PutMetricAlarmInput{
		AlarmName:          alarmName,
		Namespace:          aws.String("go-cloudwatch-alarms"),
		MetricName:         aws.String("metric"),
		Statistic:          types.StatisticAverage,
		Period:             aws.Int32(60),
		EvaluationPeriods:  aws.Int32(1),
		Threshold:          aws.Float64(2.5),
		ComparisonOperator: types.ComparisonOperatorGreaterThanThreshold,
		ActionsEnabled:     aws.Bool(true),
	})
	if err != nil {
		t.Fatal(err)
	}

	alarms, err := client.DescribeAlarms(ctx, &cloudwatch.DescribeAlarmsInput{
		AlarmNames: []string{*alarmName},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(alarms.MetricAlarms) != 1 {
		t.Fatalf("expected 1 alarm, got %d", len(alarms.MetricAlarms))
	}
	alarm := alarms.MetricAlarms[0]
	if aws.ToFloat64(alarm.Threshold) != 2.5 || !aws.ToBool(alarm.ActionsEnabled) {
		t.Fatalf("unexpected alarm: %+v", alarm)
	}
	if aws.ToTime(alarm.StateUpdatedTimestamp).IsZero() {
		t.Fatal("expected StateUpdatedTimestamp to be set")
	}

	_, err = client.DeleteAlarms(ctx, &cloudwatch.DeleteAlarmsInput{AlarmNames: []string{*alarmName}})
	if err != nil {
		t.Fatal(err)
	}
}

func TestCloudWatchErrors(t *testing.T) {
	client := newCloudWatchClient(t)

	_, err := client.GetDashboard(context.Background(), &cloudwatch.GetDashboardInput{
		DashboardName: aws.String("go-cloudwatch-unknown-dashboard"),
	})
	var notFound *types.ResourceNotFound
	if !errors.As(err, &notFound) {
		t.Fatalf("expected ResourceNotFound, got %v", err)
	}
	if notFound.ErrorMessage() != "Dashboard does not exist" {
		t.Fatalf("unexpected message: %q", notFound.ErrorMessage())
	}
}
