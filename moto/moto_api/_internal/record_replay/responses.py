import json
import random

from . import record_replay_api
from moto import settings
from moto.core.responses import BaseResponse


class RecordReplayResponse(BaseResponse):

    def reset_recording(self, request, full_url, headers):  # pylint: disable=unused-argument
        print("reset")
        record_replay_api.reset_recording()
        return 200, {}, ""

    def start_recording(
            self, request, full_url, headers
    ):  # pylint: disable=unused-argument
        print("start")
        record_replay_api.start_recording()
        return 200, {}, "Recording is set to True"

    def stop_recording(self, request, full_url, headers):  # pylint: disable=unused-argument
        print("stop")
        record_replay_api.stop_recording()
        return 200, {}, "Recording is set to False"

    def upload_recording(
        self, request, full_url, headers
    ):  # pylint: disable=unused-argument
        data = request.data
        record_replay_api.upload_recording(data)
        return 200, {}, ""

    def download_recording(
            self, request, full_url, headers
    ):  # pylint: disable=unused-argument
        data = record_replay_api.download_recording()
        return 200, {}, data

    # NOTE: Replaying assumes, for simplicity, that it is the only action
    # running against moto at the time. No recording happens while replaying.
    def replay_recording(
            self, request, full_url, headers
    ):  # pylint: disable=unused-argument
        record_replay_api.replay_recording()

        return 200, {}, ""
