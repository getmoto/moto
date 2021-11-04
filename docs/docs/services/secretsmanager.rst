.. _implementedservice_secretsmanager:

==============
secretsmanager
==============



- [ ] cancel_rotate_secret
- [X] create_secret
- [ ] delete_resource_policy
- [X] delete_secret
- [X] describe_secret
- [X] get_random_password
- [X] get_resource_policy
- [X] get_secret_value
- [X] list_secret_version_ids
- [X] list_secrets
  
        Returns secrets from secretsmanager.
        The result is paginated and page items depends on the token value, because token contains start element
        number of secret list.
        Response example:
        {
            SecretList: [
                {
                    ARN: 'arn:aws:secretsmanager:us-east-1:1234567890:secret:test1-gEcah',
                    Name: 'test1',
                    ...
                },
                {
                    ARN: 'arn:aws:secretsmanager:us-east-1:1234567890:secret:test2-KZwml',
                    Name: 'test2',
                    ...
                }
            ],
            NextToken: '2'
        }

        :param filters: (List) Filter parameters.
        :param max_results: (int) Max number of results per page.
        :param next_token: (str) Page token.
        :return: (Tuple[List,str]) Returns result list and next token.
        

- [ ] put_resource_policy
- [X] put_secret_value
- [ ] remove_regions_from_replication
- [ ] replicate_secret_to_regions
- [X] restore_secret
- [X] rotate_secret
- [ ] stop_replication_to_replica
- [X] tag_resource
- [X] untag_resource
- [X] update_secret
- [X] update_secret_version_stage
- [ ] validate_resource_policy

