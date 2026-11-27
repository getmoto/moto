"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_polly import PollyClient, PollyConfig
    from aws_sdk_polly.models import LexiconNotFoundException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-polly is not installed", allow_module_level=True)


LEXICON = """<?xml version="1.0" encoding="UTF-8"?>
<lexicon version="1.0"
      xmlns="http://www.w3.org/2005/01/pronunciation-lexicon"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.w3.org/2005/01/pronunciation-lexicon
        http://www.w3.org/TR/2007/CR-pronunciation-lexicon-20071212/pls.xsd"
      alphabet="ipa"
      xml:lang="en-US">
  <lexeme>
    <grapheme>AWS</grapheme>
    <alias>Amazon Web Services</alias>
  </lexeme>
</lexicon>"""


@pytest.mark.skip(
    reason="GetLexicon on a deleted lexicon raises an unmodeled CallError instead of LexiconNotFoundException: "
    "Moto's Polly errors have 'Content-Type: text/html' and no 'x-amzn-ErrorType' header (and status 400 instead of 404), "
    "so the SDK ignores the '__type' in the body"
)
@mock_aws
def test_narrate_with_custom_pronunciation():
    """Pick an English voice and narrate text using a custom pronunciation lexicon."""
    config = PollyConfig.resolve(region="us-east-1")
    lexicon_name = f"acronyms{uuid4().hex[:8]}"

    with PollyClient(config=config) as client:
        voices = client.describe_voices(language_code="en-US").voices
        assert voices
        assert {voice.language_code for voice in voices} == {"en-US"}
        voice = voices[0]

        client.put_lexicon(name=lexicon_name, content=LEXICON)

        lexicon = client.get_lexicon(name=lexicon_name)
        assert lexicon.lexicon.name == lexicon_name
        assert lexicon.lexicon.content == LEXICON
        assert lexicon.lexicon_attributes.alphabet == "ipa"
        assert lexicon.lexicon_attributes.language_code == "en-US"

        names = [lex.name for lex in client.list_lexicons().lexicons or []]
        assert lexicon_name in names

        speech = client.synthesize_speech(
            text="Welcome to AWS",
            voice_id=voice.id,
            output_format="mp3",
            lexicon_names=[lexicon_name],
        )
        assert speech.content_type == "audio/mpeg"
        assert speech.audio_stream.read()

        client.delete_lexicon(name=lexicon_name)
        with pytest.raises(LexiconNotFoundException):
            client.get_lexicon(name=lexicon_name)
