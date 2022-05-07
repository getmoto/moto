"""ebs base URL and path."""
from .responses import EBSResponse

url_bases = [r"https?://ebs\.(.+)\.amazonaws\.com"]


response = EBSResponse()


url_paths = {
    "{0}/snapshots$": response.snapshots,
    "{0}/snapshots/completion/(?P<snapshot_id>[^/]+)$": response.complete_snapshot,
    "{0}/snapshots/(?P<snapshot_id>[^/]+)/changedblocks$": response.snapshot_changed_blocks,
    "{0}/snapshots/(?P<snapshot_id>[^/]+)/blocks$": response.snapshot_blocks,
    "{0}/snapshots/(?P<snapshot_id>[^/]+)/blocks/(?P<block_idx>[^/]+)$": response.snapshot_block,
}
