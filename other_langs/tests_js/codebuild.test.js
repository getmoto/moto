import { BatchGetBuildsCommand, CodeBuildClient, CreateProjectCommand, StartBuildCommand, StopBuildCommand } from '@aws-sdk/client-codebuild'

process.env['AWS_ACCESS_KEY_ID'] = 'test'
process.env['AWS_SECRET_ACCESS_KEY'] = 'test'

const client = new CodeBuildClient({region: 'us-east-1', endpoint: 'http://localhost:5000'});

const projectName = "test-project-" + Math.floor(Math.random() * 10000);

const createProjectCommand = new CreateProjectCommand({
    name: projectName,
    source: {
        type: "S3",
        location: "bucketname/path/file.zip",
    },
    artifacts: {
        type: "NO_ARTIFACTS",
    },
    environment: {
        type: "LINUX_CONTAINER",
        image: "contents_not_validated",
        computeType: "BUILD_GENERAL1_SMALL",
    },
    serviceRole: "arn:aws:iam::123456789012:role/service-role/my-codebuild-service-role",
});

await client.send(createProjectCommand);

const startBuildCommand = new StartBuildCommand({projectName: projectName});
const { build } = await client.send(startBuildCommand);
console.log(build);

const batchGetBuildsCommand = new BatchGetBuildsCommand({ids: [build.id]});
const { builds } = await client.send(batchGetBuildsCommand);
console.log(builds);

const stopBuildCommand = new StopBuildCommand({id: build.id});
const response = await client.send(stopBuildCommand);
console.log(response);
