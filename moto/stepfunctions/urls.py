from .responses import StepFunctionResponse

url_bases = [
    r"https?://states\.(.+)\.amazonaws.com",
    # StartSyncExecution is sent to sync-states.<region>.amazonaws.com
    r"https?://sync-states\.(.+)\.amazonaws.com",
]

url_paths = {"{0}/$": StepFunctionResponse.dispatch}
