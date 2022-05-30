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
    "{0}/moto-api/reset-record": response_instance.reset_methods_record,
    "{0}/moto-api/start-recording": response_instance.start_recording,
    "{0}/moto-api/stop-recording": response_instance.stop_recording,
    "{0}/moto-api/replay-record": response_instance.replay_methods_from_record,
    "{0}/moto-api/set-seed": response_instance.set_seed_for_ids,
    "{0}/moto-api/load-record": response_instance.load_methods_record,
    "{0}/moto-api/dump-record": response_instance.dump_methods_record,
}
