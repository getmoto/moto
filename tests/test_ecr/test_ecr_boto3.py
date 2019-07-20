from __future__ import unicode_literals

import hashlib
import json
from datetime import datetime
from freezegun import freeze_time
import os
from random import random

import re
import sure  # noqa

import boto3
from botocore.exceptions import ClientError, ParamValidationError
from dateutil.tz import tzlocal

from moto import mock_ecr
from nose import SkipTest


def _create_image_digest(contents=None):
    if not contents:
        contents = 'docker_image{0}'.format(int(random() * 10 ** 6))
    return "sha256:%s" % hashlib.sha256(contents.encode('utf-8')).hexdigest()


def _create_image_manifest():
    return {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config":
            {
                "mediaType": "application/vnd.docker.container.image.v1+json",
                "size": 7023,
                "digest": _create_image_digest("config")
            },
        "layers": [
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 32654,
                "digest": _create_image_digest("layer1")
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 16724,
                "digest": _create_image_digest("layer2")
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 73109,
                # randomize image digest
                "digest": _create_image_digest()
            }
        ]
    }


@mock_ecr
def test_create_repository():
    client = boto3.client('ecr', region_name='us-east-1')
    response = client.create_repository(
        repositoryName='test_ecr_repository'
    )
    response['repository']['repositoryName'].should.equal('test_ecr_repository')
    response['repository']['repositoryArn'].should.equal(
        'arn:aws:ecr:us-east-1:012345678910:repository/test_ecr_repository')
    response['repository']['registryId'].should.equal('012345678910')
    response['repository']['repositoryUri'].should.equal(
        '012345678910.dkr.ecr.us-east-1.amazonaws.com/test_ecr_repository')
    # response['repository']['createdAt'].should.equal(0)


@mock_ecr
def test_describe_repositories():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository1'
    )
    _ = client.create_repository(
        repositoryName='test_repository0'
    )
    response = client.describe_repositories()
    len(response['repositories']).should.equal(2)

    respository_arns = ['arn:aws:ecr:us-east-1:012345678910:repository/test_repository1',
                        'arn:aws:ecr:us-east-1:012345678910:repository/test_repository0']
    set([response['repositories'][0]['repositoryArn'],
         response['repositories'][1]['repositoryArn']]).should.equal(set(respository_arns))

    respository_uris = ['012345678910.dkr.ecr.us-east-1.amazonaws.com/test_repository1',
                        '012345678910.dkr.ecr.us-east-1.amazonaws.com/test_repository0']
    set([response['repositories'][0]['repositoryUri'],
         response['repositories'][1]['repositoryUri']]).should.equal(set(respository_uris))


@mock_ecr
def test_describe_repositories_1():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository1'
    )
    _ = client.create_repository(
        repositoryName='test_repository0'
    )
    response = client.describe_repositories(registryId='012345678910')
    len(response['repositories']).should.equal(2)

    respository_arns = ['arn:aws:ecr:us-east-1:012345678910:repository/test_repository1',
                        'arn:aws:ecr:us-east-1:012345678910:repository/test_repository0']
    set([response['repositories'][0]['repositoryArn'],
         response['repositories'][1]['repositoryArn']]).should.equal(set(respository_arns))

    respository_uris = ['012345678910.dkr.ecr.us-east-1.amazonaws.com/test_repository1',
                        '012345678910.dkr.ecr.us-east-1.amazonaws.com/test_repository0']
    set([response['repositories'][0]['repositoryUri'],
         response['repositories'][1]['repositoryUri']]).should.equal(set(respository_uris))


@mock_ecr
def test_describe_repositories_2():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository1'
    )
    _ = client.create_repository(
        repositoryName='test_repository0'
    )
    response = client.describe_repositories(registryId='109876543210')
    len(response['repositories']).should.equal(0)


@mock_ecr
def test_describe_repositories_3():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository1'
    )
    _ = client.create_repository(
        repositoryName='test_repository0'
    )
    response = client.describe_repositories(repositoryNames=['test_repository1'])
    len(response['repositories']).should.equal(1)
    respository_arn = 'arn:aws:ecr:us-east-1:012345678910:repository/test_repository1'
    response['repositories'][0]['repositoryArn'].should.equal(respository_arn)

    respository_uri = '012345678910.dkr.ecr.us-east-1.amazonaws.com/test_repository1'
    response['repositories'][0]['repositoryUri'].should.equal(respository_uri)


@mock_ecr
def test_describe_repositories_with_image():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='latest'
    )

    response = client.describe_repositories(repositoryNames=['test_repository'])
    len(response['repositories']).should.equal(1)


@mock_ecr
def test_delete_repository():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )
    response = client.delete_repository(repositoryName='test_repository')
    response['repository']['repositoryName'].should.equal('test_repository')
    response['repository']['repositoryArn'].should.equal(
        'arn:aws:ecr:us-east-1:012345678910:repository/test_repository')
    response['repository']['registryId'].should.equal('012345678910')
    response['repository']['repositoryUri'].should.equal(
        '012345678910.dkr.ecr.us-east-1.amazonaws.com/test_repository')
    # response['repository']['createdAt'].should.equal(0)

    response = client.describe_repositories()
    len(response['repositories']).should.equal(0)


@mock_ecr
def test_put_image():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    response = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='latest'
    )

    response['image']['imageId']['imageTag'].should.equal('latest')
    response['image']['imageId']['imageDigest'].should.contain("sha")
    response['image']['repositoryName'].should.equal('test_repository')
    response['image']['registryId'].should.equal('012345678910')


@mock_ecr
def test_put_image_with_push_date():
    if os.environ.get('TEST_SERVER_MODE', 'false').lower() == 'true':
        raise SkipTest('Cant manipulate time in server mode')

    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    with freeze_time('2018-08-28 00:00:00'):
        image1_date = datetime.now()
        _ = client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag='latest'
        )

    with freeze_time('2019-05-31 00:00:00'):
        image2_date = datetime.now()
        _ = client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag='latest'
        )

    describe_response = client.describe_images(repositoryName='test_repository')

    type(describe_response['imageDetails']).should.be(list)
    len(describe_response['imageDetails']).should.be(2)

    set([describe_response['imageDetails'][0]['imagePushedAt'],
        describe_response['imageDetails'][1]['imagePushedAt']]).should.equal(set([image1_date, image2_date]))


@mock_ecr
def test_put_image_with_multiple_tags():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )
    manifest = _create_image_manifest()
    response = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(manifest),
        imageTag='v1'
    )

    response['image']['imageId']['imageTag'].should.equal('v1')
    response['image']['imageId']['imageDigest'].should.contain("sha")
    response['image']['repositoryName'].should.equal('test_repository')
    response['image']['registryId'].should.equal('012345678910')

    response1 = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(manifest),
        imageTag='latest'
    )

    response1['image']['imageId']['imageTag'].should.equal('latest')
    response1['image']['imageId']['imageDigest'].should.contain("sha")
    response1['image']['repositoryName'].should.equal('test_repository')
    response1['image']['registryId'].should.equal('012345678910')

    response2 = client.describe_images(repositoryName='test_repository')
    type(response2['imageDetails']).should.be(list)
    len(response2['imageDetails']).should.be(1)

    response2['imageDetails'][0]['imageDigest'].should.contain("sha")

    response2['imageDetails'][0]['registryId'].should.equal("012345678910")

    response2['imageDetails'][0]['repositoryName'].should.equal("test_repository")

    len(response2['imageDetails'][0]['imageTags']).should.be(2)
    response2['imageDetails'][0]['imageTags'].should.be.equal(['v1', 'latest'])


@mock_ecr
def test_list_images():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository_1'
    )

    _ = client.create_repository(
        repositoryName='test_repository_2'
    )

    _ = client.put_image(
        repositoryName='test_repository_1',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='latest'
    )

    _ = client.put_image(
        repositoryName='test_repository_1',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='v1'
    )

    _ = client.put_image(
        repositoryName='test_repository_1',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='v2'
    )

    _ = client.put_image(
        repositoryName='test_repository_2',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='oldest'
    )

    response = client.list_images(repositoryName='test_repository_1')
    type(response['imageIds']).should.be(list)
    len(response['imageIds']).should.be(3)

    image_tags = ['latest', 'v1', 'v2']
    set([response['imageIds'][0]['imageTag'],
         response['imageIds'][1]['imageTag'],
         response['imageIds'][2]['imageTag']]).should.equal(set(image_tags))

    response = client.list_images(repositoryName='test_repository_2')
    type(response['imageIds']).should.be(list)
    len(response['imageIds']).should.be(1)
    response['imageIds'][0]['imageTag'].should.equal('oldest')


@mock_ecr
def test_list_images_from_repository_that_doesnt_exist():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository_1'
    )

    # non existing repo
    error_msg = re.compile(
        r".*The repository with name 'repo-that-doesnt-exist' does not exist in the registry with id '123'.*",
        re.MULTILINE)
    client.list_images.when.called_with(
        repositoryName='repo-that-doesnt-exist',
        registryId='123',
    ).should.throw(Exception, error_msg)

    # repo does not exist in specified registry
    error_msg = re.compile(
        r".*The repository with name 'test_repository_1' does not exist in the registry with id '222'.*",
        re.MULTILINE)
    client.list_images.when.called_with(
        repositoryName='test_repository_1',
        registryId='222',
    ).should.throw(Exception, error_msg)


@mock_ecr
def test_describe_images():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest())
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='latest'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='v1'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='v2'
    )

    response = client.describe_images(repositoryName='test_repository')
    type(response['imageDetails']).should.be(list)
    len(response['imageDetails']).should.be(4)

    response['imageDetails'][0]['imageDigest'].should.contain("sha")
    response['imageDetails'][1]['imageDigest'].should.contain("sha")
    response['imageDetails'][2]['imageDigest'].should.contain("sha")
    response['imageDetails'][3]['imageDigest'].should.contain("sha")

    response['imageDetails'][0]['registryId'].should.equal("012345678910")
    response['imageDetails'][1]['registryId'].should.equal("012345678910")
    response['imageDetails'][2]['registryId'].should.equal("012345678910")
    response['imageDetails'][3]['registryId'].should.equal("012345678910")

    response['imageDetails'][0]['repositoryName'].should.equal("test_repository")
    response['imageDetails'][1]['repositoryName'].should.equal("test_repository")
    response['imageDetails'][2]['repositoryName'].should.equal("test_repository")
    response['imageDetails'][3]['repositoryName'].should.equal("test_repository")

    response['imageDetails'][0].should_not.have.key('imageTags')
    len(response['imageDetails'][1]['imageTags']).should.be(1)
    len(response['imageDetails'][2]['imageTags']).should.be(1)
    len(response['imageDetails'][3]['imageTags']).should.be(1)

    image_tags = ['latest', 'v1', 'v2']
    set([response['imageDetails'][1]['imageTags'][0],
         response['imageDetails'][2]['imageTags'][0],
         response['imageDetails'][3]['imageTags'][0]]).should.equal(set(image_tags))

    response['imageDetails'][0]['imageSizeInBytes'].should.equal(52428800)
    response['imageDetails'][1]['imageSizeInBytes'].should.equal(52428800)
    response['imageDetails'][2]['imageSizeInBytes'].should.equal(52428800)
    response['imageDetails'][3]['imageSizeInBytes'].should.equal(52428800)


@mock_ecr
def test_describe_images_by_tag():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    tag_map = {}
    for tag in ['latest', 'v1', 'v2']:
        put_response = client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag=tag
        )
        tag_map[tag] = put_response['image']

    for tag, put_response in tag_map.items():
        response = client.describe_images(repositoryName='test_repository', imageIds=[{'imageTag': tag}])
        len(response['imageDetails']).should.be(1)
        image_detail = response['imageDetails'][0]
        image_detail['registryId'].should.equal("012345678910")
        image_detail['repositoryName'].should.equal("test_repository")
        image_detail['imageTags'].should.equal([put_response['imageId']['imageTag']])
        image_detail['imageDigest'].should.equal(put_response['imageId']['imageDigest'])


@mock_ecr
def test_describe_images_tags_should_not_contain_empty_tag1():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    manifest = _create_image_manifest()
    client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(manifest)
    )

    tags = ['v1', 'v2', 'latest']
    for tag in tags:
        client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(manifest),
            imageTag=tag
        )

    response = client.describe_images(repositoryName='test_repository', imageIds=[{'imageTag': tag}])
    len(response['imageDetails']).should.be(1)
    image_detail = response['imageDetails'][0]
    len(image_detail['imageTags']).should.equal(3)
    image_detail['imageTags'].should.be.equal(tags)


@mock_ecr
def test_describe_images_tags_should_not_contain_empty_tag2():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    manifest = _create_image_manifest()
    tags = ['v1', 'v2']
    for tag in tags:
        client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(manifest),
            imageTag=tag
        )

    client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(manifest)
    )

    client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(manifest),
        imageTag='latest'
    )

    response = client.describe_images(repositoryName='test_repository', imageIds=[{'imageTag': tag}])
    len(response['imageDetails']).should.be(1)
    image_detail = response['imageDetails'][0]
    len(image_detail['imageTags']).should.equal(3)
    image_detail['imageTags'].should.be.equal(['v1', 'v2', 'latest'])


@mock_ecr
def test_describe_repository_that_doesnt_exist():
    client = boto3.client('ecr', region_name='us-east-1')

    error_msg = re.compile(
        r".*The repository with name 'repo-that-doesnt-exist' does not exist in the registry with id '123'.*",
        re.MULTILINE)
    client.describe_repositories.when.called_with(
        repositoryNames=['repo-that-doesnt-exist'],
        registryId='123',
    ).should.throw(ClientError, error_msg)

@mock_ecr
def test_describe_image_that_doesnt_exist():
    client = boto3.client('ecr', region_name='us-east-1')
    client.create_repository(repositoryName='test_repository')

    error_msg1 = re.compile(
        r".*The image with imageId {imageDigest:'null', imageTag:'testtag'} does not exist within "
        r"the repository with name 'test_repository' in the registry with id '123'.*",
        re.MULTILINE)

    client.describe_images.when.called_with(
        repositoryName='test_repository', imageIds=[{'imageTag': 'testtag'}], registryId='123',
    ).should.throw(ClientError, error_msg1)

    error_msg2 = re.compile(
        r".*The repository with name 'repo-that-doesnt-exist' does not exist in the registry with id '123'.*",
        re.MULTILINE)
    client.describe_images.when.called_with(
        repositoryName='repo-that-doesnt-exist', imageIds=[{'imageTag': 'testtag'}], registryId='123',
    ).should.throw(ClientError, error_msg2)


@mock_ecr
def test_delete_repository_that_doesnt_exist():
    client = boto3.client('ecr', region_name='us-east-1')

    error_msg = re.compile(
        r".*The repository with name 'repo-that-doesnt-exist' does not exist in the registry with id '123'.*",
        re.MULTILINE)

    client.delete_repository.when.called_with(
        repositoryName='repo-that-doesnt-exist',
        registryId='123').should.throw(
        ClientError, error_msg)


@mock_ecr
def test_describe_images_by_digest():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    tags = ['latest', 'v1', 'v2']
    digest_map = {}
    for tag in tags:
        put_response = client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(_create_image_manifest()),
            imageTag=tag
        )
        digest_map[put_response['image']['imageId']['imageDigest']] = put_response['image']

    for digest, put_response in digest_map.items():
        response = client.describe_images(repositoryName='test_repository',
                                          imageIds=[{'imageDigest': digest}])
        len(response['imageDetails']).should.be(1)
        image_detail = response['imageDetails'][0]
        image_detail['registryId'].should.equal("012345678910")
        image_detail['repositoryName'].should.equal("test_repository")
        image_detail['imageTags'].should.equal([put_response['imageId']['imageTag']])
        image_detail['imageDigest'].should.equal(digest)


@mock_ecr
def test_get_authorization_token_assume_region():
    client = boto3.client('ecr', region_name='us-east-1')
    auth_token_response = client.get_authorization_token()

    auth_token_response.should.contain('authorizationData')
    auth_token_response.should.contain('ResponseMetadata')
    auth_token_response['authorizationData'].should.equal([
        {
            'authorizationToken': 'QVdTOjAxMjM0NTY3ODkxMC1hdXRoLXRva2Vu',
            'proxyEndpoint': 'https://012345678910.dkr.ecr.us-east-1.amazonaws.com',
            'expiresAt': datetime(2015, 1, 1, tzinfo=tzlocal())
        },
    ])


@mock_ecr
def test_get_authorization_token_explicit_regions():
    client = boto3.client('ecr', region_name='us-east-1')
    auth_token_response = client.get_authorization_token(registryIds=['10987654321', '878787878787'])

    auth_token_response.should.contain('authorizationData')
    auth_token_response.should.contain('ResponseMetadata')
    auth_token_response['authorizationData'].should.equal([
        {
            'authorizationToken': 'QVdTOjEwOTg3NjU0MzIxLWF1dGgtdG9rZW4=',
            'proxyEndpoint': 'https://10987654321.dkr.ecr.us-east-1.amazonaws.com',
            'expiresAt': datetime(2015, 1, 1, tzinfo=tzlocal()),
        },
        {
            'authorizationToken': 'QVdTOjg3ODc4Nzg3ODc4Ny1hdXRoLXRva2Vu',
            'proxyEndpoint': 'https://878787878787.dkr.ecr.us-east-1.amazonaws.com',
            'expiresAt': datetime(2015, 1, 1, tzinfo=tzlocal())

        }
    ])


@mock_ecr
def test_batch_get_image():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='latest'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='v1'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='v2'
    )

    response = client.batch_get_image(
        repositoryName='test_repository',
        imageIds=[
            {
                'imageTag': 'v2'
            },
        ],
    )

    type(response['images']).should.be(list)
    len(response['images']).should.be(1)

    response['images'][0]['imageManifest'].should.contain("vnd.docker.distribution.manifest.v2+json")
    response['images'][0]['registryId'].should.equal("012345678910")
    response['images'][0]['repositoryName'].should.equal("test_repository")

    response['images'][0]['imageId']['imageTag'].should.equal("v2")
    response['images'][0]['imageId']['imageDigest'].should.contain("sha")

    type(response['failures']).should.be(list)
    len(response['failures']).should.be(0)


@mock_ecr
def test_batch_get_image_that_doesnt_exist():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='latest'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='v1'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='v2'
    )

    response = client.batch_get_image(
        repositoryName='test_repository',
        imageIds=[
            {
                'imageTag': 'v5'
            },
        ],
    )

    type(response['images']).should.be(list)
    len(response['images']).should.be(0)

    type(response['failures']).should.be(list)
    len(response['failures']).should.be(1)
    response['failures'][0]['failureReason'].should.equal("Requested image not found")
    response['failures'][0]['failureCode'].should.equal("ImageNotFound")
    response['failures'][0]['imageId']['imageTag'].should.equal("v5")


@mock_ecr
def test_batch_get_image_no_tags():
    client = boto3.client('ecr', region_name='us-east-1')
    _ = client.create_repository(
        repositoryName='test_repository'
    )

    _ = client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='latest'
    )

    error_msg = re.compile(
        r".*Missing required parameter in input: \"imageIds\".*",
        re.MULTILINE)

    client.batch_get_image.when.called_with(
        repositoryName='test_repository').should.throw(
            ParamValidationError, error_msg)


@mock_ecr
def test_batch_delete_image_by_tag():
    client = boto3.client('ecr', region_name='us-east-1')
    client.create_repository(
        repositoryName='test_repository'
    )

    manifest = _create_image_manifest()

    tags = ['v1', 'v1.0', 'latest']
    for tag in tags:
        client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(manifest),
            imageTag=tag,
        )

    describe_response1 = client.describe_images(repositoryName='test_repository')

    batch_delete_response = client.batch_delete_image(
        registryId='012345678910',
        repositoryName='test_repository',
        imageIds=[
            {
                'imageTag': 'latest'
            },
        ],
    )

    describe_response2 = client.describe_images(repositoryName='test_repository')

    type(describe_response1['imageDetails'][0]['imageTags']).should.be(list)
    len(describe_response1['imageDetails'][0]['imageTags']).should.be(3)

    type(describe_response2['imageDetails'][0]['imageTags']).should.be(list)
    len(describe_response2['imageDetails'][0]['imageTags']).should.be(2)

    type(batch_delete_response['imageIds']).should.be(list)
    len(batch_delete_response['imageIds']).should.be(1)

    batch_delete_response['imageIds'][0]['imageTag'].should.equal("latest")

    type(batch_delete_response['failures']).should.be(list)
    len(batch_delete_response['failures']).should.be(0)


@mock_ecr
def test_batch_delete_image_delete_last_tag():
    client = boto3.client('ecr', region_name='us-east-1')
    client.create_repository(
        repositoryName='test_repository'
    )

    client.put_image(
        repositoryName='test_repository',
        imageManifest=json.dumps(_create_image_manifest()),
        imageTag='v1',
    )

    describe_response1 = client.describe_images(repositoryName='test_repository')

    batch_delete_response = client.batch_delete_image(
        registryId='012345678910',
        repositoryName='test_repository',
        imageIds=[
            {
                'imageTag': 'v1'
            },
        ],
    )

    describe_response2 = client.describe_images(repositoryName='test_repository')

    type(describe_response1['imageDetails'][0]['imageTags']).should.be(list)
    len(describe_response1['imageDetails'][0]['imageTags']).should.be(1)

    type(describe_response2['imageDetails']).should.be(list)
    len(describe_response2['imageDetails']).should.be(0)

    type(batch_delete_response['imageIds']).should.be(list)
    len(batch_delete_response['imageIds']).should.be(1)

    batch_delete_response['imageIds'][0]['imageTag'].should.equal("v1")

    type(batch_delete_response['failures']).should.be(list)
    len(batch_delete_response['failures']).should.be(0)


@mock_ecr
def test_batch_delete_image_with_nonexistent_tag():
    client = boto3.client('ecr', region_name='us-east-1')
    client.create_repository(
        repositoryName='test_repository'
    )

    manifest = _create_image_manifest()

    tags = ['v1', 'v1.0', 'latest']
    for tag in tags:
        client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(manifest),
            imageTag=tag,
        )

    describe_response = client.describe_images(repositoryName='test_repository')

    missing_tag = "missing-tag"
    batch_delete_response = client.batch_delete_image(
        registryId='012345678910',
        repositoryName='test_repository',
        imageIds=[
            {
                'imageTag': missing_tag
            },
        ],
    )

    type(describe_response['imageDetails'][0]['imageTags']).should.be(list)
    len(describe_response['imageDetails'][0]['imageTags']).should.be(3)

    type(batch_delete_response['imageIds']).should.be(list)
    len(batch_delete_response['imageIds']).should.be(0)

    batch_delete_response['failures'][0]['imageId']['imageTag'].should.equal(missing_tag)
    batch_delete_response['failures'][0]['failureCode'].should.equal("ImageNotFound")
    batch_delete_response['failures'][0]['failureReason'].should.equal("Requested image not found")

    type(batch_delete_response['failures']).should.be(list)
    len(batch_delete_response['failures']).should.be(1)


@mock_ecr
def test_batch_delete_image_by_digest():
    client = boto3.client('ecr', region_name='us-east-1')
    client.create_repository(
        repositoryName='test_repository'
    )

    manifest = _create_image_manifest()

    tags = ['v1', 'v2', 'latest']
    for tag in tags:
        client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(manifest),
            imageTag=tag
        )

    describe_response = client.describe_images(repositoryName='test_repository')
    image_digest = describe_response['imageDetails'][0]['imageDigest']

    batch_delete_response = client.batch_delete_image(
        registryId='012345678910',
        repositoryName='test_repository',
        imageIds=[
            {
                'imageDigest': image_digest
            },
        ],
    )

    describe_response = client.describe_images(repositoryName='test_repository')

    type(describe_response['imageDetails']).should.be(list)
    len(describe_response['imageDetails']).should.be(0)

    type(batch_delete_response['imageIds']).should.be(list)
    len(batch_delete_response['imageIds']).should.be(3)

    batch_delete_response['imageIds'][0]['imageDigest'].should.equal(image_digest)
    batch_delete_response['imageIds'][1]['imageDigest'].should.equal(image_digest)
    batch_delete_response['imageIds'][2]['imageDigest'].should.equal(image_digest)

    set([
        batch_delete_response['imageIds'][0]['imageTag'],
        batch_delete_response['imageIds'][1]['imageTag'],
        batch_delete_response['imageIds'][2]['imageTag']]).should.equal(set(tags))

    type(batch_delete_response['failures']).should.be(list)
    len(batch_delete_response['failures']).should.be(0)


@mock_ecr
def test_batch_delete_image_with_invalid_digest():
    client = boto3.client('ecr', region_name='us-east-1')
    client.create_repository(
        repositoryName='test_repository'
    )

    manifest = _create_image_manifest()

    tags = ['v1', 'v2', 'latest']
    for tag in tags:
        client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(manifest),
            imageTag=tag
        )

    invalid_image_digest = 'sha256:invalid-digest'

    batch_delete_response = client.batch_delete_image(
        registryId='012345678910',
        repositoryName='test_repository',
        imageIds=[
            {
                'imageDigest': invalid_image_digest
            },
        ],
    )

    type(batch_delete_response['imageIds']).should.be(list)
    len(batch_delete_response['imageIds']).should.be(0)

    type(batch_delete_response['failures']).should.be(list)
    len(batch_delete_response['failures']).should.be(1)

    batch_delete_response['failures'][0]['imageId']['imageDigest'].should.equal(invalid_image_digest)
    batch_delete_response['failures'][0]['failureCode'].should.equal("InvalidImageDigest")
    batch_delete_response['failures'][0]['failureReason'].should.equal("Invalid request parameters: image digest should satisfy the regex '[a-zA-Z0-9-_+.]+:[a-fA-F0-9]+'")


@mock_ecr
def test_batch_delete_image_with_missing_parameters():
    client = boto3.client('ecr', region_name='us-east-1')
    client.create_repository(
        repositoryName='test_repository'
    )

    batch_delete_response = client.batch_delete_image(
        registryId='012345678910',
        repositoryName='test_repository',
        imageIds=[
            {
            },
        ],
    )

    type(batch_delete_response['imageIds']).should.be(list)
    len(batch_delete_response['imageIds']).should.be(0)

    type(batch_delete_response['failures']).should.be(list)
    len(batch_delete_response['failures']).should.be(1)

    batch_delete_response['failures'][0]['failureCode'].should.equal("MissingDigestAndTag")
    batch_delete_response['failures'][0]['failureReason'].should.equal("Invalid request parameters: both tag and digest cannot be null")


@mock_ecr
def test_batch_delete_image_with_matching_digest_and_tag():
    client = boto3.client('ecr', region_name='us-east-1')
    client.create_repository(
        repositoryName='test_repository'
    )

    manifest = _create_image_manifest()

    tags = ['v1', 'v1.0', 'latest']
    for tag in tags:
        client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(manifest),
            imageTag=tag
        )

    describe_response = client.describe_images(repositoryName='test_repository')
    image_digest = describe_response['imageDetails'][0]['imageDigest']

    batch_delete_response = client.batch_delete_image(
        registryId='012345678910',
        repositoryName='test_repository',
        imageIds=[
            {
                'imageDigest': image_digest,
                'imageTag': 'v1'
            },
        ],
    )

    describe_response = client.describe_images(repositoryName='test_repository')

    type(describe_response['imageDetails']).should.be(list)
    len(describe_response['imageDetails']).should.be(0)

    type(batch_delete_response['imageIds']).should.be(list)
    len(batch_delete_response['imageIds']).should.be(3)

    batch_delete_response['imageIds'][0]['imageDigest'].should.equal(image_digest)
    batch_delete_response['imageIds'][1]['imageDigest'].should.equal(image_digest)
    batch_delete_response['imageIds'][2]['imageDigest'].should.equal(image_digest)

    set([
        batch_delete_response['imageIds'][0]['imageTag'],
        batch_delete_response['imageIds'][1]['imageTag'],
        batch_delete_response['imageIds'][2]['imageTag']]).should.equal(set(tags))

    type(batch_delete_response['failures']).should.be(list)
    len(batch_delete_response['failures']).should.be(0)


@mock_ecr
def test_batch_delete_image_with_mismatched_digest_and_tag():
    client = boto3.client('ecr', region_name='us-east-1')
    client.create_repository(
        repositoryName='test_repository'
    )

    manifest = _create_image_manifest()

    tags = ['v1', 'latest']
    for tag in tags:
        client.put_image(
            repositoryName='test_repository',
            imageManifest=json.dumps(manifest),
            imageTag=tag
        )

    describe_response = client.describe_images(repositoryName='test_repository')
    image_digest = describe_response['imageDetails'][0]['imageDigest']

    batch_delete_response = client.batch_delete_image(
        registryId='012345678910',
        repositoryName='test_repository',
        imageIds=[
            {
                'imageDigest': image_digest,
                'imageTag': 'v2'
            },
        ],
    )

    type(batch_delete_response['imageIds']).should.be(list)
    len(batch_delete_response['imageIds']).should.be(0)

    type(batch_delete_response['failures']).should.be(list)
    len(batch_delete_response['failures']).should.be(1)

    batch_delete_response['failures'][0]['imageId']['imageDigest'].should.equal(image_digest)
    batch_delete_response['failures'][0]['imageId']['imageTag'].should.equal("v2")
    batch_delete_response['failures'][0]['failureCode'].should.equal("ImageNotFound")
    batch_delete_response['failures'][0]['failureReason'].should.equal("Requested image not found")
