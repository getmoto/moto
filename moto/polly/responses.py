import json
import re
from typing import Any

from moto.core.responses import BaseResponse

from .exceptions import (
    InvalidParameterValue,
    InvalidSampleRateException,
    MarksNotSupportedForFormatException,
    MissingParameter,
    SsmlMarksNotSupportedForTextTypeException,
    TextLengthExceededException,
    ValidationException,
)
from .models import PollyBackend, polly_backends
from .resources import LANGUAGE_CODES, VOICE_IDS

LEXICON_NAME_REGEX = re.compile(r"^[0-9A-Za-z]{1,20}$")


class PollyResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="polly")

    @property
    def polly_backend(self) -> PollyBackend:
        return polly_backends[self.current_account][self.region]

    @property
    def json(self) -> dict[str, Any]:  # type: ignore[misc]
        if not hasattr(self, "_json"):
            self._json = json.loads(self.body)
        return self._json

    def describe_voices(self) -> str:
        language_code = self._get_param("LanguageCode")

        if language_code is not None and language_code not in LANGUAGE_CODES:
            all_codes = ", ".join(LANGUAGE_CODES)  # type: ignore
            msg = (
                f"1 validation error detected: Value '{language_code}' at 'languageCode' failed to satisfy constraint: "
                f"Member must satisfy enum value set: [{all_codes}]"
            )
            raise ValidationException(msg)

        voices = self.polly_backend.describe_voices(language_code)

        return json.dumps({"Voices": voices})

    def put_lexicon(self) -> str:
        lexicon_name = self._get_param("LexiconName")
        if LEXICON_NAME_REGEX.match(lexicon_name) is None:
            raise InvalidParameterValue("Lexicon name must match [0-9A-Za-z]{1,20}")

        if "Content" not in self.json:
            raise MissingParameter("Content is missing from the body")

        self.polly_backend.put_lexicon(lexicon_name, self.json["Content"])

        return ""

    def list_lexicons(self) -> str:
        result = {"Lexicons": self.polly_backend.list_lexicons()}

        return json.dumps(result)

    def get_lexicon(self) -> str:
        lexicon_name = self._get_param("LexiconName")
        lexicon = self.polly_backend.get_lexicon(lexicon_name)

        result = {
            "Lexicon": {"Name": lexicon_name, "Content": lexicon.content},
            "LexiconAttributes": lexicon.to_dict()["Attributes"],
        }

        return json.dumps(result)

    def delete_lexicon(self) -> str:
        lexicon_name = self._get_param("LexiconName")
        self.polly_backend.delete_lexicon(lexicon_name)

        return ""

    def synthesize_speech(self) -> tuple[str, dict[str, Any]]:
        # Sanity check params
        args = {
            "lexicon_names": None,
            "sample_rate": 22050,
            "speech_marks": None,
            "text": None,
            "text_type": "text",
        }

        if "LexiconNames" in self.json:
            for lex in self.json["LexiconNames"]:
                self.polly_backend.get_lexicon(lex)

            args["lexicon_names"] = self.json["LexiconNames"]

        if "OutputFormat" not in self.json:
            raise MissingParameter("Missing parameter OutputFormat")
        if self.json["OutputFormat"] not in ("json", "mp3", "ogg_vorbis", "pcm"):
            raise InvalidParameterValue("Not one of json, mp3, ogg_vorbis, pcm")
        args["output_format"] = self.json["OutputFormat"]

        if "SampleRate" in self.json:
            sample_rate = int(self.json["SampleRate"])
            if sample_rate not in (8000, 16000, 22050):
                raise InvalidSampleRateException()
            args["sample_rate"] = sample_rate

        if "SpeechMarkTypes" in self.json:
            for value in self.json["SpeechMarkTypes"]:
                if value not in ("sentance", "ssml", "viseme", "word"):
                    raise InvalidParameterValue(
                        "Not one of sentance, ssml, viseme, word"
                    )
            args["speech_marks"] = self.json["SpeechMarkTypes"]

        if "Text" not in self.json:
            raise MissingParameter("Missing parameter Text")
        args["text"] = self.json["Text"]

        if "TextType" in self.json:
            if self.json["TextType"] not in ("ssml", "text"):
                raise InvalidParameterValue("Not one of ssml, text")
            args["text_type"] = self.json["TextType"]

        if "VoiceId" not in self.json:
            raise MissingParameter("Missing parameter VoiceId")
        if self.json["VoiceId"] not in VOICE_IDS:
            all_voices = ", ".join(VOICE_IDS)  # type: ignore
            raise InvalidParameterValue(f"Not one of {all_voices}")
        args["voice_id"] = self.json["VoiceId"]

        # More validation
        if len(args["text"]) > 3000:  # type: ignore
            raise TextLengthExceededException()

        if args["speech_marks"] is not None and args["output_format"] != "json":
            raise MarksNotSupportedForFormatException()
        if args["speech_marks"] is not None and args["text_type"] == "text":
            raise SsmlMarksNotSupportedForTextTypeException()

        content_type = "audio/json"
        if args["output_format"] == "mp3":
            content_type = "audio/mpeg"
        elif args["output_format"] == "ogg_vorbis":
            content_type = "audio/ogg"
        elif args["output_format"] == "pcm":
            content_type = "audio/pcm"

        headers = {"Content-Type": content_type}

        return "\x00\x00\x00\x00\x00\x00\x00\x00", headers
