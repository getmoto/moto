from .responses import BatchResponse

url_bases = [r"https?://batch\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/v1/createcomputeenvironment$": BatchResponse.dispatch,
    "{0}/v1/describecomputeenvironments$": BatchResponse.dispatch,
    "{0}/v1/deletecomputeenvironment": BatchResponse.dispatch,
    "{0}/v1/updatecomputeenvironment": BatchResponse.dispatch,
    "{0}/v1/createjobqueue": BatchResponse.dispatch,
    "{0}/v1/describejobqueues": BatchResponse.dispatch,
    "{0}/v1/updatejobqueue": BatchResponse.dispatch,
    "{0}/v1/deletejobqueue": BatchResponse.dispatch,
    "{0}/v1/registerjobdefinition": BatchResponse.dispatch,
    "{0}/v1/deregisterjobdefinition": BatchResponse.dispatch,
    "{0}/v1/describejobdefinitions": BatchResponse.dispatch,
    "{0}/v1/submitjob": BatchResponse.dispatch,
    "{0}/v1/describejobs": BatchResponse.dispatch,
    "{0}/v1/listjobs": BatchResponse.dispatch,
    "{0}/v1/terminatejob": BatchResponse.dispatch,
    "{0}/v1/canceljob": BatchResponse.dispatch,
}
