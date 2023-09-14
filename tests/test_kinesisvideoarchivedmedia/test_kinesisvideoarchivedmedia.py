import boto3
from moto import mock_kinesisvideoarchivedmedia
from moto import mock_kinesisvideo
from moto.core.utils import utcnow
from datetime import timedelta


@mock_kinesisvideo
@mock_kinesisvideoarchivedmedia
def test_get_hls_streaming_session_url():
    region_name = "ap-northeast-1"
    kvs_client = boto3.client("kinesisvideo", region_name=region_name)
    stream_name = "my-stream"
    kvs_client.create_stream(StreamName=stream_name)

    api_name = "GET_HLS_STREAMING_SESSION_URL"
    res = kvs_client.get_data_endpoint(StreamName=stream_name, APIName=api_name)
    data_endpoint = res["DataEndpoint"]

    client = boto3.client(
        "kinesis-video-archived-media",
        region_name=region_name,
        endpoint_url=data_endpoint,
    )
    res = client.get_hls_streaming_session_url(StreamName=stream_name)
    assert res["HLSStreamingSessionURL"].startswith(
        f"{data_endpoint}/hls/v1/getHLSMasterPlaylist.m3u8?SessionToken="
    )


@mock_kinesisvideo
@mock_kinesisvideoarchivedmedia
def test_get_dash_streaming_session_url():
    region_name = "ap-northeast-1"
    kvs_client = boto3.client("kinesisvideo", region_name=region_name)
    stream_name = "my-stream"
    kvs_client.create_stream(StreamName=stream_name)

    api_name = "GET_DASH_STREAMING_SESSION_URL"
    res = kvs_client.get_data_endpoint(StreamName=stream_name, APIName=api_name)
    data_endpoint = res["DataEndpoint"]

    client = boto3.client(
        "kinesis-video-archived-media",
        region_name=region_name,
        endpoint_url=data_endpoint,
    )
    res = client.get_dash_streaming_session_url(StreamName=stream_name)
    assert res["DASHStreamingSessionURL"].startswith(
        f"{data_endpoint}/dash/v1/getDASHManifest.mpd?SessionToken="
    )


@mock_kinesisvideo
@mock_kinesisvideoarchivedmedia
def test_get_clip():
    region_name = "ap-northeast-1"
    kvs_client = boto3.client("kinesisvideo", region_name=region_name)
    stream_name = "my-stream"
    kvs_client.create_stream(StreamName=stream_name)

    api_name = "GET_DASH_STREAMING_SESSION_URL"
    res = kvs_client.get_data_endpoint(StreamName=stream_name, APIName=api_name)
    data_endpoint = res["DataEndpoint"]

    client = boto3.client(
        "kinesis-video-archived-media",
        region_name=region_name,
        endpoint_url=data_endpoint,
    )
    end_timestamp = utcnow() - timedelta(hours=1)
    start_timestamp = end_timestamp - timedelta(minutes=5)
    res = client.get_clip(
        StreamName=stream_name,
        ClipFragmentSelector={
            "FragmentSelectorType": "PRODUCER_TIMESTAMP",
            "TimestampRange": {
                "StartTimestamp": start_timestamp,
                "EndTimestamp": end_timestamp,
            },
        },
    )
    assert res["ContentType"] == "video/mp4"
    assert "Payload" in res
