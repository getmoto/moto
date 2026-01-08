import boto3
import pytest
from moto import mock_aws

@mock_aws
def test_list_thing_principals_v2():
    # 1. 建立一個假的 AWS IoT 客戶端
    client = boto3.client("iot", region_name="us-east-1")
    thing_name = "my-test-thing"
    
    # 2. 建立一個 Thing (不然查不到東西)
    client.create_thing(thingName=thing_name)
    
    # 3. 呼叫剛寫好的 V2 功能！
    # (IF沒寫好，這裡就會報錯說 "Not Implemented")
    response = client.list_thing_principals_v2(thingName=thing_name)
    
    # 4. 驗證回傳的資料裡面，有沒有 V2 專屬的欄位 "thingPrincipalObjects"
    assert "thingPrincipalObjects" in response
    # 因為我們還沒綁定證書，所以列表應該是空的，但 key 必須存在
    assert response["thingPrincipalObjects"] == []

    print("\n🎉 測試成功！V2 功能正常運作中！")