.. _recorder_page:

.. role:: raw-html(raw)
    :format: html

=============================
Recorder
=============================

The Moto Recorder is used to log all incoming requests, which can be replayed at a later date.
This is useful if you need to setup an initial state, and ensure that this is the same across developers/environments.

Usage
##############

Usage in decorator mode:

.. sourcecode:: python

    from moto.moto_api import recorder

    # Start the recorder
    recorder.start_recording()
    # Make some requests using boto3

    # When you're ready..
    recorder.stop_recording()
    log = recorder.download_recording()

    # Later on, upload this log to another system
    recorder.upload_recording(log)
    # And replay the contents
    recorder.replay_recording()

    # While the recorder is active, new requests will be appended to the existing log
    # Reset the current log if you want to start with an empty slate
    recorder.reset_recording()

Usage in ServerMode:

.. sourcecode:: python

    # Start the recorder
    requests.post("http://localhost:5000/moto-api/record-replay/start-recording")
    # Make some requests

    # When you're ready..
    requests.post("http://localhost:5000/moto-api/record-replay/stop-recording")
    log = requests.get("http://localhost:5000/moto-api/record-replay/download-recording").content

    # Later on, upload this log to another system
    requests.post("http://localhost:5000/moto-api/record-replay/upload-recording", data=log)
    # and replay the contents
    requests.post("http://localhost:5000/moto-api/record-replay/replay-recording")

    # While the recorder is active, new requests will be appended to the existing log
    # Reset the current log if you want to start with an empty slate
    requests.post("http://localhost:5000/moto-api/record-replay/reset-recording")

Note that this feature records and replays the incoming HTTP request. Randomized data created by Moto, such as resource ID's, will not be stored as part of the log.
