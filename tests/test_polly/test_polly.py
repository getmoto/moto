from __future__ import unicode_literals

from botocore.exceptions import ClientError
import boto3
import sure  # noqa
from moto import mock_polly

# Polly only available in a few regions
DEFAULT_REGION = 'eu-west-1'

LEXICON_XML = """<?xml version="1.0" encoding="UTF-8"?>
<lexicon version="1.0" 
      xmlns="http://www.w3.org/2005/01/pronunciation-lexicon"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xsi:schemaLocation="http://www.w3.org/2005/01/pronunciation-lexicon 
        http://www.w3.org/TR/2007/CR-pronunciation-lexicon-20071212/pls.xsd"
      alphabet="ipa" 
      xml:lang="en-US">
  <lexeme>
    <grapheme>W3C</grapheme>
    <alias>World Wide Web Consortium</alias>
  </lexeme>
</lexicon>"""


@mock_polly
def test_describe_voices():
    client = boto3.client('polly', region_name=DEFAULT_REGION)

    resp = client.describe_voices()
    len(resp['Voices']).should.be.greater_than(1)

    resp = client.describe_voices(LanguageCode='en-GB')
    len(resp['Voices']).should.equal(3)

    try:
        client.describe_voices(LanguageCode='SOME_LANGUAGE')
    except ClientError as err:
        err.response['Error']['Code'].should.equal('400')
    else:
        raise RuntimeError('Should of raised an exception')


@mock_polly
def test_put_list_lexicon():
    client = boto3.client('polly', region_name=DEFAULT_REGION)

    # Return nothing
    client.put_lexicon(
        Name='test',
        Content=LEXICON_XML
    )

    resp = client.list_lexicons()
    len(resp['Lexicons']).should.equal(1)


@mock_polly
def test_put_get_lexicon():
    client = boto3.client('polly', region_name=DEFAULT_REGION)

    # Return nothing
    client.put_lexicon(
        Name='test',
        Content=LEXICON_XML
    )

    resp = client.get_lexicon(Name='test')
    resp.should.contain('Lexicon')
    resp.should.contain('LexiconAttributes')


@mock_polly
def test_put_lexicon_bad_name():
    client = boto3.client('polly', region_name=DEFAULT_REGION)

    try:
        client.put_lexicon(
            Name='test-invalid',
            Content=LEXICON_XML
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('InvalidParameterValue')
    else:
        raise RuntimeError('Should of raised an exception')


@mock_polly
def test_synthesize_speech():
    client = boto3.client('polly', region_name=DEFAULT_REGION)

    # Return nothing
    client.put_lexicon(
        Name='test',
        Content=LEXICON_XML
    )

    a = client.synthesize_speech(
        LexiconNames=['test'],
        OutputFormat='pcm',
        SampleRate='16000',
        Text='test1234',
        TextType='text',
        VoiceId='Astrid'
    )
    # TODO check content type
    print()

# Todo expand synthesize speech tests for bad config