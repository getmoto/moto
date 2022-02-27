.. _implementedservice_managedblockchain:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=================
managedblockchain
=================

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_managedblockchain
            def test_managedblockchain_behaviour:
                boto3.client("managedblockchain")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_member
- [X] create_network
- [X] create_node
- [X] create_proposal
- [X] delete_member
- [X] delete_node
- [X] get_member
- [X] get_network
- [X] get_node
- [X] get_proposal
- [X] list_invitations
- [X] list_members
- [X] list_networks
- [X] list_nodes
- [X] list_proposal_votes
- [X] list_proposals
- [ ] list_tags_for_resource
- [X] reject_invitation
- [ ] tag_resource
- [ ] untag_resource
- [X] update_member
- [X] update_node
- [X] vote_on_proposal

