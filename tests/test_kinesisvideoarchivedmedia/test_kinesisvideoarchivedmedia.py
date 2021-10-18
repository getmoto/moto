import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_kinesisvideoarchivedmedia
from moto import mock_kinesisvideo
from datetime import datetime, timedelta


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
    res = client.get_hls_streaming_session_url(StreamName=stream_name,)
    reg_exp = r"^{}/hls/v1/getHLSMasterPlaylist.m3u8\?SessionToken\=.+$".format(
        data_endpoint
    )
    res.should.have.key("HLSStreamingSessionURL").which.should.match(reg_exp)


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
    res = client.get_dash_streaming_session_url(StreamName=stream_name,)
    reg_exp = r"^{}/dash/v1/getDASHManifest.mpd\?SessionToken\=.+$".format(
        data_endpoint
    )
    res.should.have.key("DASHStreamingSessionURL").which.should.match(reg_exp)


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
    end_timestamp = datetime.utcnow() - timedelta(hours=1)
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
    res.should.have.key("ContentType").which.should.match("video/mp4")
    res.should.have.key("Payload")
