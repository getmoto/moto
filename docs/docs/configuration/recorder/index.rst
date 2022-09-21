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
    requests.post("http://localhost:5000/moto-api/recorder/start-recording")
    # Make some requests

    # When you're ready..
    requests.post("http://localhost:5000/moto-api/recorder/stop-recording")
    log = requests.get("http://localhost:5000/moto-api/recorder/download-recording").content

    # Later on, upload this log to another system
    requests.post("http://localhost:5000/moto-api/recorder/upload-recording", data=log)
    # and replay the contents
    requests.post("http://localhost:5000/moto-api/recorder/replay-recording")

    # While the recorder is active, new requests will be appended to the existing log
    # Reset the current log if you want to start with an empty slate
    requests.post("http://localhost:5000/moto-api/recorder/reset-recording")

Note that this feature records and replays the incoming HTTP request. Randomized data created by Moto, such as resource ID's, will not be stored as part of the log.


Configuration
##################

The requests are stored in a file called `moto_recording`, in the directory that Python is run from. You can configure this location using the following environment variable:
`MOTO_RECORDER_FILEPATH=/whatever/path/you/want`

The recorder is disabled by default. If you want to enable it, use the following environment variable:
`MOTO_ENABLE_RECORDING=True`


Deterministic Identifiers
##############################

Moto creates random identifiers, just like AWS, for most resources. The Recorder will recreate the same resources every time, but the identifiers will always be different.

You can seed Moto to get around this problem, ensuring that the 'random' identifiers are always the same for subsequent requests.

Example invocation:

.. sourcecode:: python

    from moto.moto_api import mock_random

    mock_random.seed(42)

    # To try this out, generate a EC2 instance
    client = boto3.client("ec2", region_name="us-east-1")
    resp = client.run_instances(ImageId="ami-12c6146b", MinCount=1, MaxCount=1)

    # The resulting InstanceId will always be the same
    instance_id = resp["Instances"][0]["InstanceId"]
    assert instance_id == "i-b57056d5352b3f0b3"

To seed Moto in ServerMode:

.. sourcecode:: python

    requests.post(f"http://localhost:5000/moto-api/seed?a=42")

