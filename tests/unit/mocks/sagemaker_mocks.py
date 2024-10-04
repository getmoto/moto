class MockPipelineSession:
    def __init__(self):
        self.pipelines = {}

    def create_pipeline(self, pipeline_name, pipeline_definition):
        self.pipelines[pipeline_name] = pipeline_definition
        return {"PipelineArn": f"arn:aws:sagemaker:region:account:pipeline/{pipeline_name}"}

    def start_pipeline(self, pipeline_name):
        if pipeline_name in self.pipelines:
            return {"PipelineExecutionArn": f"arn:aws:sagemaker:region:account:pipeline/{pipeline_name}/execution/example"}
        else:
            raise ValueError(f"Pipeline {pipeline_name} not found")

    def list_pipelines(self):
        return {"PipelineSummaries": [{"PipelineName": name} for name in self.pipelines.keys()]}