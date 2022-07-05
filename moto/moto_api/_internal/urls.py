from moto.moto_api._internal.responses import MotoAPIResponse

url_bases = ["https?://motoapi.amazonaws.com"]

response_instance = MotoAPIResponse()

url_paths = {
    "{0}/moto-api/$": response_instance.dashboard,
    "{0}/moto-api/data.json": response_instance.model_data,
    "{0}/moto-api/reset": response_instance.reset_response,
    "{0}/moto-api/reset-auth": response_instance.reset_auth_response,
    "{0}/moto-api/state-manager/get-transition": response_instance.get_transition,
    "{0}/moto-api/state-manager/set-transition": response_instance.set_transition,
    "{0}/moto-api/state-manager/unset-transition": response_instance.unset_transition,
    "{0}/moto-api/set-seed": response_instance.set_seed,
    "{0}/moto-api/reset-recording": response_instance.reset_recording,
    "{0}/moto-api/start-recording": response_instance.start_recording,
    "{0}/moto-api/stop-recording": response_instance.stop_recording,
    "{0}/moto-api/upload-recording": response_instance.upload_recording,
    "{0}/moto-api/download-recording": response_instance.download_recording,
    "{0}/moto-api/replay-recording": response_instance.replay_recording,
}
