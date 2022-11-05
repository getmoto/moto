from ... import recorder
from moto.core.responses import BaseResponse


class RecorderResponse(BaseResponse):
    def reset_recording(self, req, url, headers):  # pylint: disable=unused-argument
        recorder.reset_recording()
        return 200, {}, ""

    def start_recording(self, req, url, headers):  # pylint: disable=unused-argument
        recorder.start_recording()
        return 200, {}, "Recording is set to True"

    def stop_recording(self, req, url, headers):  # pylint: disable=unused-argument
        recorder.stop_recording()
        return 200, {}, "Recording is set to False"

    def upload_recording(self, req, url, headers):  # pylint: disable=unused-argument
        data = req.data
        recorder.upload_recording(data)
        return 200, {}, ""

    def download_recording(self, req, url, headers):  # pylint: disable=unused-argument
        data = recorder.download_recording()
        return 200, {}, data

    # NOTE: Replaying assumes, for simplicity, that it is the only action
    # running against moto at the time. No recording happens while replaying.
    def replay_recording(self, req, url, headers):  # pylint: disable=unused-argument
        recorder.replay_recording(target_host=url)
        return 200, {}, ""
