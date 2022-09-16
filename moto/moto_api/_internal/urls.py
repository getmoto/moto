from .responses import MotoAPIResponse
from .record_replay.responses import RecordReplayResponse

url_bases = ["https?://motoapi.amazonaws.com"]

response_instance = MotoAPIResponse()
record_replay = RecordReplayResponse()

url_paths = {
    "{0}/moto-api/$": response_instance.dashboard,
    "{0}/moto-api/data.json": response_instance.model_data,
    "{0}/moto-api/reset": response_instance.reset_response,
    "{0}/moto-api/reset-auth": response_instance.reset_auth_response,
    "{0}/moto-api/state-manager/get-transition": response_instance.get_transition,
    "{0}/moto-api/state-manager/set-transition": response_instance.set_transition,
    "{0}/moto-api/state-manager/unset-transition": response_instance.unset_transition,
    "{0}/moto-api/record-replay/reset-recording": record_replay.reset_recording,
    "{0}/moto-api/record-replay/start-recording": record_replay.start_recording,
    "{0}/moto-api/record-replay/stop-recording": record_replay.stop_recording,
    "{0}/moto-api/record-replay/upload-recording": record_replay.upload_recording,
    "{0}/moto-api/record-replay/download-recording": record_replay.download_recording,
    "{0}/moto-api/record-replay/replay-recording": record_replay.replay_recording,
}
