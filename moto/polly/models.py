from xml.etree import ElementTree as ET
import datetime

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict

from .resources import VOICE_DATA
from .utils import make_arn_for_lexicon


class Lexicon(BaseModel):
    def __init__(self, name, content, account_id, region_name):
        self.name = name
        self.content = content
        self.size = 0
        self.alphabet = None
        self.last_modified = None
        self.language_code = None
        self.lexemes_count = 0
        self.arn = make_arn_for_lexicon(account_id, name, region_name)

        self.update()

    def update(self, content=None):
        if content is not None:
            self.content = content

        # Probably a very naive approach, but it'll do for now.
        try:
            root = ET.fromstring(self.content)
            self.size = len(self.content)
            self.last_modified = int(
                (
                    datetime.datetime.now() - datetime.datetime(1970, 1, 1)
                ).total_seconds()
            )
            self.lexemes_count = len(root.findall("."))

            for key, value in root.attrib.items():
                if key.endswith("alphabet"):
                    self.alphabet = value
                elif key.endswith("lang"):
                    self.language_code = value

        except Exception as err:
            raise ValueError("Failure parsing XML: {0}".format(err))

    def to_dict(self):
        return {
            "Attributes": {
                "Alphabet": self.alphabet,
                "LanguageCode": self.language_code,
                "LastModified": self.last_modified,
                "LexemesCount": self.lexemes_count,
                "LexiconArn": self.arn,
                "Size": self.size,
            }
        }

    def __repr__(self):
        return "<Lexicon {0}>".format(self.name)


class PollyBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self._lexicons = {}

    def describe_voices(self, language_code):
        """
        Pagination is not yet implemented
        """
        if language_code is None:
            return VOICE_DATA

        return [item for item in VOICE_DATA if item["LanguageCode"] == language_code]

    def delete_lexicon(self, name):
        # implement here
        del self._lexicons[name]

    def get_lexicon(self, name):
        # Raises KeyError
        return self._lexicons[name]

    def list_lexicons(self):
        """
        Pagination is not yet implemented
        """

        result = []

        for name, lexicon in self._lexicons.items():
            lexicon_dict = lexicon.to_dict()
            lexicon_dict["Name"] = name

            result.append(lexicon_dict)

        return result

    def put_lexicon(self, name, content):
        # If lexicon content is bad, it will raise ValueError
        if name in self._lexicons:
            # Regenerated all the stats from the XML
            # but keeps the ARN
            self._lexicons.update(content)
        else:
            lexicon = Lexicon(
                name, content, self.account_id, region_name=self.region_name
            )
            self._lexicons[name] = lexicon


polly_backends = BackendDict(PollyBackend, "polly")
