package main

import (
	"fmt"
	"strings"
	"testing"
)

func TestDescribeStream(t *testing.T) {

	result := DescribeStream()
	streamArn := *result.StreamDescription.StreamArn
	checkFor := TableName + "/stream/"
	fmt.Println(streamArn)
	if strings.Contains(streamArn, checkFor) == false {
		t.Errorf("StreamArn does not contain our table name [%s].", TableName)
	}
}
