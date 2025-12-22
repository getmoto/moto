from sagemaker.modules.configs import InputData, SourceCode
from sagemaker.modules.train import ModelTrainer

from moto import mock_aws


@mock_aws
def test_model_trainer():
    # https://sagemaker.readthedocs.io/en/stable/overview.html#using-modeltrainer

    # Image URI for the training job
    pytorch_image = (
        "763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:2.0.0-cpu-py310"
    )

    # Define the script to be run
    source_code = SourceCode(
        source_dir=".",
        entry_script="custom_script.py",
    )

    # Define the ModelTrainer
    model_trainer = ModelTrainer(
        # SageMaker always calls `get_caller_identity`
        # If no role is provided, it will also call `get_role` on the output of `get_caller_identity`
        # That fails against Moto, because Moto's `get_caller_identity` returns a User, instead of a Role
        # If we pass a custom role, SageMaker does not explicitly call `get_role`, and therefore does not fail
        #
        # TODO
        # AFAIK, AWS also returns a User when calling `get_caller_identity`
        # We should investigate why SageMaker behaves like this/what SageMaker expects to happen
        role="arn:aws:sts::000000000000:user/moto",
        training_image=pytorch_image,
        source_code=source_code,
        base_job_name="script-mode",
    )

    # Pass the input data
    input_data = InputData(
        channel_name="train",
        data_source="s3://some/path",  # S3 path where training data is stored
    )

    # Start the training job
    model_trainer.train(input_data_config=[input_data], wait=True)
