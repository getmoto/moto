def make_arn_for_lexicon(account_id: str, name: str, region_name: str) -> str:
    return f"arn:aws:polly:{region_name}:{account_id}:lexicon/{name}"
