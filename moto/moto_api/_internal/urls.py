from .responses import MotoAPIResponse
from .recorder.responses import RecorderResponse

url_bases = ["https?://motoapi.amazonaws.com"]

response_instance = MotoAPIResponse()
recorder_response = RecorderResponse()

url_paths = {
    "{0}/moto-api/$": response_instance.dashboard,
    "{0}/moto-api/data.json": response_instance.model_data,
    "{0}/moto-api/reset": response_instance.reset_response,
    "{0}/moto-api/reset-auth": response_instance.reset_auth_response,
    "{0}/moto-api/seed": response_instance.seed,
    "{0}/moto-api/static/athena/query-results": response_instance.set_athena_result,
    "{0}/moto-api/static/sagemaker/endpoint-results": response_instance.set_sagemaker_result,
    "{0}/moto-api/static/rds-data/statement-results": response_instance.set_rds_data_result,
    "{0}/moto-api/state-manager/get-transition": response_instance.get_transition,
    "{0}/moto-api/state-manager/set-transition": response_instance.set_transition,
    "{0}/moto-api/state-manager/unset-transition": response_instance.unset_transition,
    "{0}/moto-api/recorder/reset-recording": recorder_response.reset_recording,
    "{0}/moto-api/recorder/start-recording": recorder_response.start_recording,
    "{0}/moto-api/recorder/stop-recording": recorder_response.stop_recording,
    "{0}/moto-api/recorder/upload-recording": recorder_response.upload_recording,
    "{0}/moto-api/recorder/download-recording": recorder_response.download_recording,
    "{0}/moto-api/recorder/replay-recording": recorder_response.replay_recording,
}
