"""RekognitionBackend class with methods for supported APIs."""

import random
import string

from moto.core import BaseBackend
from moto.core.utils import BackendDict


class RekognitionBackend(BaseBackend):
    """Implementation of Rekognition APIs."""

    def __init__(self, region_name=None):
        self.region_name = region_name

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def start_text_detection(self):
        return self._job_id()

    def get_text_detection(self):
        """
        This returns hardcoded values and none of the parameters are taken into account.
        """
        return (
            self._job_status(),
            self._status_message(),
            self._video_metadata(),
            self._text_detections(),
            self._next_token(),
            self._text_model_version(),
        )

    # private

    def _job_id(self):
        return "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(64)
        )

    def _job_status(self):
        return "SUCCEEDED"

    def _next_token(self):
        return ""

    def _status_message(self):
        return ""

    def _text_model_version(self):
        return "3.1"

    def _video_metadata(self):
        return {
            "Codec": "h264",
            "DurationMillis": 15020,
            "Format": "QuickTime / MOV",
            "FrameRate": 24.0,
            "FrameHeight": 720,
            "FrameWidth": 1280,
            "ColorRange": "LIMITED",
        }

    def _text_detections(self):
        return [
            {
                "Timestamp": 0,
                "TextDetection": {
                    "DetectedText": "Hello world",
                    "Type": "LINE",
                    "Id": 0,
                    "Confidence": 97.89398956298828,
                    "Geometry": {
                        "BoundingBox": {
                            "Width": 0.1364741027355194,
                            "Height": 0.0318513885140419,
                            "Left": 0.4310702085494995,
                            "Top": 0.876121461391449,
                        },
                        "Polygon": [
                            {"X": 0.4310702085494995, "Y": 0.8769540190696716},
                            {"X": 0.5673548579216003, "Y": 0.876121461391449},
                            {"X": 0.5675443410873413, "Y": 0.90714031457901},
                            {"X": 0.4312596917152405, "Y": 0.9079728722572327},
                        ],
                    },
                },
            },
            {
                "Timestamp": 0,
                "TextDetection": {
                    "DetectedText": "Hello",
                    "Type": "WORD",
                    "Id": 1,
                    "ParentId": 0,
                    "Confidence": 99.1568832397461,
                    "Geometry": {
                        "BoundingBox": {
                            "Width": 0.0648193359375,
                            "Height": 0.0234375,
                            "Left": 0.43121337890625,
                            "Top": 0.876953125,
                        },
                        "Polygon": [
                            {"X": 0.43121337890625, "Y": 0.876953125},
                            {"X": 0.49603271484375, "Y": 0.876953125},
                            {"X": 0.49603271484375, "Y": 0.900390625},
                            {"X": 0.43121337890625, "Y": 0.900390625},
                        ],
                    },
                },
            },
            {
                "Timestamp": 0,
                "TextDetection": {
                    "DetectedText": "world",
                    "Type": "WORD",
                    "Id": 2,
                    "ParentId": 0,
                    "Confidence": 96.63108825683594,
                    "Geometry": {
                        "BoundingBox": {
                            "Width": 0.07103776931762695,
                            "Height": 0.02804870530962944,
                            "Left": 0.4965003430843353,
                            "Top": 0.8795245885848999,
                        },
                        "Polygon": [
                            {"X": 0.4965003430843353, "Y": 0.8809727430343628},
                            {"X": 0.5673661231994629, "Y": 0.8795245885848999},
                            {"X": 0.5675381422042847, "Y": 0.9061251282691956},
                            {"X": 0.4966723322868347, "Y": 0.9075732827186584},
                        ],
                    },
                },
            },
            {
                "Timestamp": 1000,
                "TextDetection": {
                    "DetectedText": "Goodbye world",
                    "Type": "LINE",
                    "Id": 0,
                    "Confidence": 98.9729995727539,
                    "Geometry": {
                        "BoundingBox": {
                            "Width": 0.13677978515625,
                            "Height": 0.0302734375,
                            "Left": 0.43121337890625,
                            "Top": 0.876953125,
                        },
                        "Polygon": [
                            {"X": 0.43121337890625, "Y": 0.876953125},
                            {"X": 0.5679931640625, "Y": 0.876953125},
                            {"X": 0.5679931640625, "Y": 0.9072265625},
                            {"X": 0.43121337890625, "Y": 0.9072265625},
                        ],
                    },
                },
            },
            {
                "Timestamp": 1000,
                "TextDetection": {
                    "DetectedText": "Goodbye",
                    "Type": "WORD",
                    "Id": 1,
                    "ParentId": 0,
                    "Confidence": 99.7258529663086,
                    "Geometry": {
                        "BoundingBox": {
                            "Width": 0.0648193359375,
                            "Height": 0.0234375,
                            "Left": 0.43121337890625,
                            "Top": 0.876953125,
                        },
                        "Polygon": [
                            {"X": 0.43121337890625, "Y": 0.876953125},
                            {"X": 0.49603271484375, "Y": 0.876953125},
                            {"X": 0.49603271484375, "Y": 0.900390625},
                            {"X": 0.43121337890625, "Y": 0.900390625},
                        ],
                    },
                },
            },
            {
                "Timestamp": 1000,
                "TextDetection": {
                    "DetectedText": "world",
                    "Type": "WORD",
                    "Id": 2,
                    "ParentId": 0,
                    "Confidence": 98.22015380859375,
                    "Geometry": {
                        "BoundingBox": {
                            "Width": 0.0703125,
                            "Height": 0.0263671875,
                            "Left": 0.4976806640625,
                            "Top": 0.880859375,
                        },
                        "Polygon": [
                            {"X": 0.4976806640625, "Y": 0.880859375},
                            {"X": 0.5679931640625, "Y": 0.880859375},
                            {"X": 0.5679931640625, "Y": 0.9072265625},
                            {"X": 0.4976806640625, "Y": 0.9072265625},
                        ],
                    },
                },
            },
        ]


rekognition_backends = BackendDict(RekognitionBackend, "rekognition")
