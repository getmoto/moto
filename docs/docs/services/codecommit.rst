.. _implementedservice_codecommit:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
codecommit
==========



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_codecommit
            def test_codecommit_behaviour:
                boto3.client("codecommit")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] associate_approval_rule_template_with_repository
- [ ] batch_associate_approval_rule_template_with_repositories
- [ ] batch_describe_merge_conflicts
- [ ] batch_disassociate_approval_rule_template_from_repositories
- [ ] batch_get_commits
- [ ] batch_get_repositories
- [ ] create_approval_rule_template
- [ ] create_branch
- [ ] create_commit
- [ ] create_pull_request
- [ ] create_pull_request_approval_rule
- [X] create_repository
- [ ] create_unreferenced_merge_commit
- [ ] delete_approval_rule_template
- [ ] delete_branch
- [ ] delete_comment_content
- [ ] delete_file
- [ ] delete_pull_request_approval_rule
- [X] delete_repository
- [ ] describe_merge_conflicts
- [ ] describe_pull_request_events
- [ ] disassociate_approval_rule_template_from_repository
- [ ] evaluate_pull_request_approval_rules
- [ ] get_approval_rule_template
- [ ] get_blob
- [ ] get_branch
- [ ] get_comment
- [ ] get_comment_reactions
- [ ] get_comments_for_compared_commit
- [ ] get_comments_for_pull_request
- [ ] get_commit
- [ ] get_differences
- [ ] get_file
- [ ] get_folder
- [ ] get_merge_commit
- [ ] get_merge_conflicts
- [ ] get_merge_options
- [ ] get_pull_request
- [ ] get_pull_request_approval_states
- [ ] get_pull_request_override_state
- [X] get_repository
- [ ] get_repository_triggers
- [ ] list_approval_rule_templates
- [ ] list_associated_approval_rule_templates_for_repository
- [ ] list_branches
- [ ] list_pull_requests
- [ ] list_repositories
- [ ] list_repositories_for_approval_rule_template
- [ ] list_tags_for_resource
- [ ] merge_branches_by_fast_forward
- [ ] merge_branches_by_squash
- [ ] merge_branches_by_three_way
- [ ] merge_pull_request_by_fast_forward
- [ ] merge_pull_request_by_squash
- [ ] merge_pull_request_by_three_way
- [ ] override_pull_request_approval_rules
- [ ] post_comment_for_compared_commit
- [ ] post_comment_for_pull_request
- [ ] post_comment_reply
- [ ] put_comment_reaction
- [ ] put_file
- [ ] put_repository_triggers
- [ ] tag_resource
- [ ] test_repository_triggers
- [ ] untag_resource
- [ ] update_approval_rule_template_content
- [ ] update_approval_rule_template_description
- [ ] update_approval_rule_template_name
- [ ] update_comment
- [ ] update_default_branch
- [ ] update_pull_request_approval_rule_content
- [ ] update_pull_request_approval_state
- [ ] update_pull_request_description
- [ ] update_pull_request_status
- [ ] update_pull_request_title
- [ ] update_repository_description
- [ ] update_repository_name

