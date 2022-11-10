"""RekognitionBackend class with methods for supported APIs."""

import string

from moto.core import BaseBackend
from moto.core.utils import BackendDict
from moto.moto_api._internal import mock_random as random


class RekognitionBackend(BaseBackend):
    """Implementation of Rekognition APIs."""

    def start_face_search(self):
        return self._job_id()

    def start_text_detection(self):
        return self._job_id()

    def get_face_search(self):
        """
        This returns hardcoded values and none of the parameters are taken into account.
        """
        return (
            self._job_status(),
            self._status_message(),
            self._video_metadata(),
            self._persons(),
            self._next_token(),
            self._text_model_version(),
        )

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

    def _persons(self):
        return [
            {
                "Timestamp": 0,
                "Person": {
                    "Index": 0,
                    "Face": {
                        "BoundingBox": {
                            "Width": 0.42217350006103516,
                            "Height": 0.9352386593818665,
                            "Left": 0.31870967149734497,
                            "Top": -0.0049947104416787624,
                        },
                        "Landmarks": [
                            {
                                "Type": "eyeLeft",
                                "X": 0.4800040125846863,
                                "Y": 0.23425640165805817,
                            },
                            {
                                "Type": "eyeRight",
                                "X": 0.63795405626297,
                                "Y": 0.19219470024108887,
                            },
                            {
                                "Type": "mouthLeft",
                                "X": 0.5283276438713074,
                                "Y": 0.6190487146377563,
                            },
                            {
                                "Type": "mouthRight",
                                "X": 0.660395085811615,
                                "Y": 0.5830448269844055,
                            },
                            {
                                "Type": "nose",
                                "X": 0.619724690914154,
                                "Y": 0.3800361752510071,
                            },
                        ],
                        "Pose": {
                            "Roll": -5.063229084014893,
                            "Yaw": 18.038856506347656,
                            "Pitch": 12.567241668701172,
                        },
                        "Quality": {
                            "Brightness": 83.42264556884766,
                            "Sharpness": 67.22731018066406,
                        },
                        "Confidence": 99.99860382080078,
                    },
                },
                "FaceMatches": [
                    {
                        "Similarity": 99.99994659423828,
                        "Face": {
                            "FaceId": "f2489050-020e-4c14-8693-63339847a59d",
                            "BoundingBox": {
                                "Width": 0.7136539816856384,
                                "Height": 0.9471719861030579,
                                "Left": 0.19036999344825745,
                                "Top": -0.012074699625372887,
                            },
                            "ImageId": "f3b180d3-f5ad-39c1-b825-ba30b170a90d",
                            "ExternalImageId": "Dave_Bloggs",
                            "Confidence": 99.99970245361328,
                        },
                    },
                    {
                        "Similarity": 99.9986572265625,
                        "Face": {
                            "FaceId": "f0d22a6a-3436-4d23-ae5b-c5cb2e795581",
                            "BoundingBox": {
                                "Width": 0.7198730111122131,
                                "Height": 1.003640055656433,
                                "Left": 0.1844159960746765,
                                "Top": -0.00142729002982378,
                            },
                            "ImageId": "738d14f3-26be-3066-b1a9-7f4f6bb3ffc6",
                            "ExternalImageId": "Dave_Bloggs",
                            "Confidence": 99.99939727783203,
                        },
                    },
                    {
                        "Similarity": 99.99791717529297,
                        "Face": {
                            "FaceId": "c48162bd-a16a-4e04-ad3c-967761895295",
                            "BoundingBox": {
                                "Width": 0.7364680171012878,
                                "Height": 1.0104399919509888,
                                "Left": 0.1361449956893921,
                                "Top": -0.009593159891664982,
                            },
                            "ImageId": "eae3565c-741b-342c-8e73-379a09ae5346",
                            "ExternalImageId": "Dave_Bloggs",
                            "Confidence": 99.99949645996094,
                        },
                    },
                    {
                        "Similarity": 99.37212371826172,
                        "Face": {
                            "FaceId": "651314bb-28d4-405d-9b13-c32e9ff28299",
                            "BoundingBox": {
                                "Width": 0.3711090087890625,
                                "Height": 0.3609749972820282,
                                "Left": 0.2571589946746826,
                                "Top": 0.21493400633335114,
                            },
                            "ImageId": "068700f5-0b2e-39c0-874b-2c58fa10d833",
                            "ExternalImageId": "Dave_Bloggs",
                            "Confidence": 99.99300384521484,
                        },
                    },
                ],
            }
        ]

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
