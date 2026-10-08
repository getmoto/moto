from moto.cloudhsmv2.models import Backup


def test_backup():
    backup = Backup(
        cluster_id="test",
        hsm_type="test",
        mode="test",
        tag_list=None,
        source_backup="test",
        source_cluster="test",
        source_region="test",
        never_expires=False,
        region_name="us-east-1",
    )
    dict = backup.to_dict()
    assert dict["ClusterId"] == "test"
    assert dict["HsmType"] == "test"
    assert dict["Mode"] == "test"
    assert dict["SourceBackup"] == "test"
    assert dict["SourceCluster"] == "test"
    assert dict["SourceRegion"] == "test"
    assert not dict["NeverExpires"]
    assert "arn:aws:cloudhsm:us-east-1" in dict["BackupArn"]
