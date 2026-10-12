# AWS Docs: https://docs.aws.amazon.com/general/latest/gr/elb.html

DEFAULT_HOSTED_ZONE_ID = "Z2P70J7EXAMPLE"

ALB_CLB_HOSTED_ZONE_IDS: dict[str, str] = {
    "af-south-1": "Z268VQBMOI5EKX",
    "ap-east-1": "Z3DQVH9N71FHZ0",
    "ap-east-2": "Z02789141MW7T1WBU19PO",
    "ap-northeast-1": "Z14GRHDCWA56QT",
    "ap-northeast-2": "ZWKZPGTI48KDX",
    "ap-northeast-3": "Z5LXEXXYW11ES",
    "ap-south-1": "ZP97RAFLXTNZK",
    "ap-south-2": "Z0173938T07WNTVAEPZN",
    "ap-southeast-1": "Z1LMS91P8CMLE5",
    "ap-southeast-2": "Z1GM3OXH4ZPM65",
    "ap-southeast-3": "Z08888821HLRG5A9ZRTER",
    "ap-southeast-4": "Z09517862IB2WZLPXG76F",
    "ap-southeast-5": "Z06010284QMVVW7WO5J",
    "ap-southeast-6": "Z023301818UFJ50CIO0MV",
    "ap-southeast-7": "Z0390008CMBRTHFGWBCB",
    "ca-central-1": "ZQSVJUPU6J1EY",
    "ca-west-1": "Z06473681N0SF6OS049SD",
    "cn-north-1": "Z1GDH35T77C1KE",
    "cn-northwest-1": "ZM7IZAIOVVDZF",
    "eu-central-1": "Z215JYRZR1TBD5",
    "eu-central-2": "Z06391101F2ZOEP8P5EB3",
    "eu-north-1": "Z23TAZ6LKFMNIO",
    "eu-south-1": "Z3ULH7SSC9OV64",
    "eu-south-2": "Z0956581394HF5D5LXGAP",
    "eu-west-1": "Z32O12XQLNTSW2",
    "eu-west-2": "ZHURV8PSTC4K8",
    "eu-west-3": "Z3Q77PNBQS71R4",
    "il-central-1": "Z09170902867EHPV2DABU",
    "me-central-1": "Z08230872XQRWHG2XF6I",
    "me-south-1": "ZS929ML54UICD",
    "mx-central-1": "Z023552324OKD1BB28BH5",
    "sa-east-1": "Z2P70J7HTTTPLU",
    "us-east-1": "Z35SXDOTRQ7X7K",
    "us-east-2": "Z3AADJGX6KTTL2",
    "us-gov-east-1": "Z166TLBEWOO7G0",
    "us-gov-west-1": "Z33AYJ8TM3BH4J",
    "us-west-1": "Z368ELLRRE2KJ0",
    "us-west-2": "Z1H1FL5HABSF5",
}

NLB_HOSTED_ZONE_IDS: dict[str, str] = {
    "af-south-1": "Z203XCE67M25HM",
    "ap-east-1": "Z12Y7K3UBGUAD1",
    "ap-east-2": "Z09176273OC2HWIAUNYW",
    "ap-northeast-1": "Z31USIVHYNEOWT",
    "ap-northeast-2": "ZIBE1TIR4HY56",
    "ap-northeast-3": "Z1GWIQ4HH19I5X",
    "ap-south-1": "ZVDDRBQ08TROA",
    "ap-south-2": "Z0711778386UTO08407HT",
    "ap-southeast-1": "ZKVM4W9LS7TM",
    "ap-southeast-2": "ZCT6FZBF4DROD",
    "ap-southeast-3": "Z01971771FYVNCOVWJU1G",
    "ap-southeast-4": "Z01156963G8MIIL7X90IV",
    "ap-southeast-5": "Z026317210H9ACVTRO6FB",
    "ap-southeast-6": "Z01392953RKV2Q3RBP0KU",
    "ap-southeast-7": "Z054363131YWATEMWRG5L",
    "ca-central-1": "Z2EPGBW3API2WT",
    "ca-west-1": "Z02754302KBB00W2LKWZ9",
    "cn-north-1": "Z3QFB96KMJ7ED6",
    "cn-northwest-1": "ZQEIKTCZ8352D",
    "eu-central-1": "Z3F0SRJ5LGBH90",
    "eu-central-2": "Z02239872DOALSIDCX66S",
    "eu-north-1": "Z1UDT6IFJ4EJM",
    "eu-south-1": "Z23146JA1KNAFP",
    "eu-south-2": "Z1011216NVTVYADP1SSV",
    "eu-west-1": "Z2IFOLAFXWLO4F",
    "eu-west-2": "ZD4D7Y8KGAS4G",
    "eu-west-3": "Z1CMS0P5QUZ6D5",
    "il-central-1": "Z0313266YDI6ZRHTGQY4",
    "me-central-1": "Z00282643NTTLPANJJG2P",
    "me-south-1": "Z3QSRYVP46NYYV",
    "mx-central-1": "Z02031231H3ID6HYJ9A7U",
    "sa-east-1": "ZTK26PT1VY4CU",
    "us-east-1": "Z26RNL4JYFTOTI",
    "us-east-2": "ZLMOA37VPKANP",
    "us-gov-east-1": "Z1ZSMQQ6Q24QQ8",
    "us-gov-west-1": "ZMG1MZ2THAWF1",
    "us-west-1": "Z24FKFUX50B4VW",
    "us-west-2": "Z18D5FSROUN65G",
}


def get_hosted_zone_id(region_name: str, load_balancer_type: str = "classic") -> str:
    zone_ids = (
        NLB_HOSTED_ZONE_IDS
        if load_balancer_type == "network"
        else ALB_CLB_HOSTED_ZONE_IDS
    )
    return zone_ids.get(region_name, DEFAULT_HOSTED_ZONE_ID)
