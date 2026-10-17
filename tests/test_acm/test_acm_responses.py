import pytest

from moto.acm.responses import AWSCertificateManagerResponse


def test_add_tags_to_certificate_with_none_arn():
    client = AWSCertificateManagerResponse()
    client.querystring = {
        "CertificateArn": [None],
        "Tags": [None],
    }
    with pytest.raises(Exception) as exc:
        client.add_tags_to_certificate()
    assert "ValidationException" in str(exc.value)
    assert "parameter for the specified action is not supplied." in str(exc.value)


def test_delete_certificate_with_none_arn():
    client = AWSCertificateManagerResponse()
    client.querystring = {"CertificateArn": [None]}
    with pytest.raises(Exception) as exc:
        client.delete_certificate()
    assert "ValidationException" in str(exc.value)
    assert "parameter for the specified action is not supplied." in str(exc.value)


def test_describe_certificate_with_none_arn():
    client = AWSCertificateManagerResponse()
    client.querystring = {"CertificateArn": [None]}
    with pytest.raises(Exception) as exc:
        client.describe_certificate()
    assert "ValidationException" in str(exc.value)
    assert "parameter for the specified action is not supplied." in str(exc.value)


def test_get_certificate_with_none_arn():
    client = AWSCertificateManagerResponse()
    client.querystring = {"CertificateArn": [None]}
    with pytest.raises(Exception) as exc:
        client.get_certificate()
    assert "ValidationException" in str(exc.value)
    assert "parameter for the specified action is not supplied." in str(exc.value)


def test_list_tags_for_certificate_with_none_arn():
    client = AWSCertificateManagerResponse()
    client.querystring = {"CertificateArn": [None]}
    with pytest.raises(Exception) as exc:
        client.list_tags_for_certificate()
    assert "ValidationException" in str(exc.value)
    assert "parameter for the specified action is not supplied." in str(exc.value)


def test_remove_tags_from_certificate_with_none_arn():
    client = AWSCertificateManagerResponse()
    client.querystring = {
        "CertificateArn": [None],
        "Tags": [None],
    }
    with pytest.raises(Exception) as exc:
        client.remove_tags_from_certificate()
    assert "ValidationException" in str(exc.value)
    assert "parameter for the specified action is not supplied." in str(exc.value)


def test_resend_validation_email_with_none_arn():
    client = AWSCertificateManagerResponse()
    client.querystring = {
        "CertificateArn": [None],
        "Domain": [None],
    }
    with pytest.raises(Exception) as exc:
        client.resend_validation_email()
    assert "ValidationException" in str(exc.value)
    assert "parameter for the specified action is not supplied." in str(exc.value)


def test_export_certificate_with_none_arn():
    client = AWSCertificateManagerResponse()
    client.querystring = {
        "CertificateArn": [None],
        "Passphrase": [None],
    }
    with pytest.raises(Exception) as exc:
        client.export_certificate()
    assert "ValidationException" in str(exc.value)
    assert "parameter for the specified action is not supplied." in str(exc.value)
