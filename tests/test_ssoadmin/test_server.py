import json
import sure  # noqa # pylint: disable=unused-import

import moto.server as server


def test_ssoadmin_list():
    backend = server.create_backend_app("sso-admin")
    test_client = backend.test_client()

    headers = {
        "X-Amz-Target": "SWBExternalService.ListAccountAssignments",
        "User-Agent": "aws-cli/2.2.47 Python/3.8.8 Linux/5.11.0-44-generic exe/x86_64.ubuntu.20 prompt/off command/sso-admin.list-account-assignments",
    }
    data = {
        "InstanceArn": "arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
        "AccountId": "222222222222",
        "PermissionSetArn": "arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/ps-hhhhkkkkppppoooo",
    }

    resp = test_client.post("/", headers=headers, data=json.dumps(data))

    resp.status_code.should.equal(200)
    json.loads(resp.data).should.equal({"AccountAssignments": []})
