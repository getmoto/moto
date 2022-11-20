def make_arn_for_lexicon(account_id, name, region_name):
    return f"arn:aws:polly:{region_name}:{account_id}:lexicon/{name}"
