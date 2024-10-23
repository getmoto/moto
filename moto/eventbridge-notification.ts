#!/usr/bin/env node

import * as cdk from '@aws-cdk/core';
import * as events from '@aws-cdk/aws-events';
import * as targets from '@aws-cdk/aws-events-targets';
import * as lambda from '@aws-cdk/aws-lambda';

class EventbridgeNotificationStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define a Lambda function
    const myFunction = new lambda.Function(this, 'MyFunction', {
      runtime: lambda.Runtime.NODEJS_14_X,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
        exports.handler = async (event) => {
          console.log("Event received:", JSON.stringify(event, null, 2));
          return {
            statusCode: 200,
            body: JSON.stringify('Hello from Lambda!'),
          };
        };
      `),
    });

    // Create an EventBridge rule
    const rule = new events.Rule(this, 'Rule', {
      eventPattern: {
        source: ['my.source'],
      },
    });

    // Add the Lambda function as a target.
    rule.addTarget(new targets.LambdaFunction(myFunction));
  }
}

const app = new cdk.App();
new EventbridgeNotificationStack(app, 'EventbridgeNotificationStack');
