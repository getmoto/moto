.. _implementedservice_budgets:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=======
budgets
=======

.. autoclass:: moto.budgets.models.BudgetsBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_budgets
            def test_budgets_behaviour:
                boto3.client("budgets")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_budget
- [ ] create_budget_action
- [X] create_notification
- [ ] create_subscriber
- [X] delete_budget
- [ ] delete_budget_action
- [X] delete_notification
- [ ] delete_subscriber
- [X] describe_budget
- [ ] describe_budget_action
- [ ] describe_budget_action_histories
- [ ] describe_budget_actions_for_account
- [ ] describe_budget_actions_for_budget
- [ ] describe_budget_notifications_for_account
- [ ] describe_budget_performance_history
- [X] describe_budgets
  
        Pagination is not yet implemented
        

- [X] describe_notifications_for_budget
  
        Pagination has not yet been implemented
        

- [ ] describe_subscribers_for_notification
- [ ] execute_budget_action
- [ ] update_budget
- [ ] update_budget_action
- [ ] update_notification
- [ ] update_subscriber

