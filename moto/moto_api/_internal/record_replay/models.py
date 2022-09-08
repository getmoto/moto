import base64
import json
import os
from botocore.awsrequest import AWSPreparedRequest


class RecordReplayAPI:

    def __init__(self):
        self._location = str(os.environ.get("MOTO_RECORDING_FILEPATH", "moto_recording"))
        self._os_enabled = bool(os.environ.get("MOTO_ENABLE_RECORDING", False))
        self._user_enabled = self._os_enabled

    def record_request(self, request):
        if not self._user_enabled:
            return

        if isinstance(request, AWSPreparedRequest):
            entry = {
                "module": request.__module__,
                "response_type": request.__class__.__name__,
                "headers": dict(request.headers),
                "method": request.method,
                "url": request.url,
                "body": base64.b64encode(request.body).decode('ascii'),
            }
        else:
            try:
                body = request._cached_data
                body = base64.b64encode(body).decode('ascii')
            except AttributeError:
                body = None
            entry = {
                "module": request.__module__,
                "response_type": request.__class__.__name__,
                "headers": dict(request.headers),
                "method": request.method,
                "url": request.url,
                "body": body,
            }
        if "moto-api/record-replay" in entry["url"]:
            return
        filepath = self._location
        with open(filepath, "a+") as file:
            file.write(json.dumps(entry))
            file.write("\n")

    def reset_recording(self):
        filepath = self._location
        with open(filepath, "w"):
            pass

    def start_recording(self):
        self._user_enabled = True

    def stop_recording(self):
        self._user_enabled = False

    def upload_recording(self, data):
        filepath = self._location
        with open(filepath, "bw") as file:
            file.write(data)

    def download_recording(self):
        filepath = self._location
        with open(filepath, "r") as file:
            return file.read()

    def replay_recording(self):
        filepath = self._location

        # do not record the replay itself
        old_setting = self._user_enabled
        self._user_enabled = False

        from moto.core.models import botocore_stubber

        with open(filepath, "r") as file:
            entries = file.readlines()

        for row in entries:
            row_loaded = json.loads(row)
            request = AWSPreparedRequest(method=row_loaded.get("method"), url=row_loaded.get("url"), headers=row_loaded.get("headers"), body=row_loaded.get("body"), stream_output=None)
            botocore_stubber(request)

        # restore the recording setting
        self._user_enabled = old_setting
