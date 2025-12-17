from moto import mock_aws


@mock_aws
def test_pipeline_session():
    # High-level integration test to verify Moto works with
    # SageMaker PipelineSession and step_args-based ProcessingStep.
    # This follows the docs flow without executing real jobs.
    import boto3
    from sagemaker.processing import ScriptProcessor
    from sagemaker.workflow.pipeline import Pipeline
    from sagemaker.workflow.pipeline_context import PipelineSession
    from sagemaker.workflow.steps import ProcessingStep

    region = "us-east-1"

    # Create a PipelineSession that uses Moto-backed clients
    boto_sess = boto3.Session(region_name=region)
    sm_client = boto_sess.client("sagemaker", region_name=region)
    session = PipelineSession(boto_session=boto_sess, sagemaker_client=sm_client)

    # Ensure a role exists; some SDK flows may look it up
    import json

    iam = boto_sess.client("iam", region_name=region)
    role_name = "MyRole"
    iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps({}))
    role = f"arn:aws:iam::000000000000:role/{role_name}"

    # Define a simple processor. The image URI is not validated by Moto here,
    # as we only build a pipeline definition (no job execution).
    image_uri = "763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-processing:2.0.0-cpu-py310"
    processor = ScriptProcessor(
        image_uri=image_uri,
        role=role,
        command=["python3"],
        instance_type="ml.m5.xlarge",
        instance_count=1,
        sagemaker_session=session,
    )

    # Build step args via the new interface (processor.run -> step_args)
    import os

    code_path = os.path.join(os.path.dirname(__file__), "custom_script.py")
    # Upload to S3 to avoid Windows path parsing issues in the SDK
    s3 = boto_sess.client("s3", region_name=region)
    bucket = "sm-pipeline-bucket"
    s3.create_bucket(Bucket=bucket)
    with open(code_path, "rb") as f:
        s3.put_object(Bucket=bucket, Key="code/custom_script.py", Body=f.read())
    code_uri = f"s3://{bucket}/code/custom_script.py"
    step_args = processor.run(code=code_uri, arguments=["--foo", "bar"])
    step = ProcessingStep(name="MyProcessing", step_args=step_args)

    # Create a pipeline and register it with SageMaker via Moto
    pipeline = Pipeline(
        name="MyPipeline",
        steps=[step],
        sagemaker_session=session,
    )

    pipeline.create(role_arn=role)
    execution = pipeline.start()
    assert execution.arn is not None
