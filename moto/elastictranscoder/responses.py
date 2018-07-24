# Only mock response without implementation of logic in backend
from moto.core.responses import BaseResponse
from .models import elastictranscoder_backends
import json


DEFAULT_REGION_NAME = 'us-east-1'


class ElastictranscoderResponse(BaseResponse):
    SERVICE_NAME = 'elastictranscoder'

    @property
    def elastictranscoder_backend(self):
        return elastictranscoder_backends[self.region]

    @classmethod
    def create_preset(clazz, request, full_url, headers):
        headers['content-type'] = 'application/json'
        resp = json.loads(CREATE_PRESET_RESP)
        return 201, headers, json.dumps(resp)

    @classmethod
    def create_job(clazz, request, full_url, headers):
        print(request.__dict__)
        headers['content-type'] = 'application/json'
        resp = json.loads(CREATE_JOB_RESP)
        return 201, headers, json.dumps(resp)

    @classmethod
    def check_job(clazz, request, full_url, headers):
        headers['content-type'] = 'application/json'
        resp = json.loads(CHECK_JOB_RESP)
        return 201, headers, json.dumps(resp)

    @classmethod
    def delete_preset(clazz, request, full_url, headers):
        headers['content-type'] = 'application/json'
        return 200, headers, json.dumps(dict())


CHECK_JOB_RESP = """
{
   "Job":{
      "Id":"3333333333333-abcde3",
      "PipelineId":"1111111111111-abcde1",
      "Status":"Progressing"
   }
}
"""


CREATE_JOB_RESP = """
{
   "Job":{
      "Id":"3333333333333-abcde3",
      "PipelineId":"1111111111111-abcde1",
      "Status":"Progressing"
   }
}
"""


CREATE_PRESET_RESP = """
{
   "Preset":{
      "Id":"5555555555555-abcde5",
      "Type":"Custom",
      "Name":"DefaultPreset",
      "Description":"Use for published videos",
      "Container":"mp4",
      "Audio":{
         "Codec":"AAC",
         "CodecOptions":{
            "Profile":"AAC-LC"
         },
         "SampleRate":"44100",
         "BitRate":"96",
         "Channels":"2"
      },
      "Video":{
         "Codec":"H.264",
         "CodecOptions":{
            "Profile":"main",
            "Level":"2.2",
            "MaxReferenceFrames":"3",
            "MaxBitRate":"",
            "BufferSize":"",
            "InterlacedMode":"Progressive",
            "ColorSpaceConversionMode":"None|Bt709ToBt601|Bt601ToBt709|Auto"
         },
         "KeyframesMaxDist":"240",
         "FixedGOP":"false",
         "BitRate":"1600",
         "FrameRate":"auto",
         "MaxFrameRate":"30",
         "MaxWidth":"auto",
         "MaxHeight":"auto",
         "SizingPolicy":"Fit",
         "PaddingPolicy":"Pad",
         "DisplayAspectRatio":"auto",
         "Watermarks":[
            {
               "Id":"company logo",
               "MaxWidth":"20%",
               "MaxHeight":"20%",
               "SizingPolicy":"ShrinkToFit",
               "HorizontalAlign":"Right",
               "HorizontalOffset":"10px",
               "VerticalAlign":"Bottom",
               "VerticalOffset":"10px",
               "Opacity":"55.5",
               "Target":"Content"
            }
         ]
      },
      "Thumbnails":{
         "Format":"png",
         "Interval":"120",
         "MaxWidth":"auto",
         "MaxHeight":"auto",
         "SizingPolicy":"Fit",
         "PaddingPolicy":"Pad"
      }
   },
   "Warning":""
}
"""
