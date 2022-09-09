import json

from moto.core.responses import BaseResponse
from .models import budgets_backends


class BudgetsResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="budgets")

    @property
    def backend(self):
        return budgets_backends[self.current_account]["global"]

    def create_budget(self):
        account_id = self._get_param("AccountId")
        budget = self._get_param("Budget")
        notifications = self._get_param("NotificationsWithSubscribers", [])
        self.backend.create_budget(
            account_id=account_id, budget=budget, notifications=notifications
        )
        return json.dumps(dict())

    def describe_budget(self):
        account_id = self._get_param("AccountId")
        budget_name = self._get_param("BudgetName")
        budget = self.backend.describe_budget(
            account_id=account_id, budget_name=budget_name
        )
        return json.dumps(dict(Budget=budget))

    def describe_budgets(self):
        account_id = self._get_param("AccountId")
        budgets = self.backend.describe_budgets(account_id=account_id)
        return json.dumps(dict(Budgets=budgets, nextToken=None))

    def delete_budget(self):
        account_id = self._get_param("AccountId")
        budget_name = self._get_param("BudgetName")
        self.backend.delete_budget(account_id=account_id, budget_name=budget_name)
        return json.dumps(dict())

    def create_notification(self):
        account_id = self._get_param("AccountId")
        budget_name = self._get_param("BudgetName")
        notification = self._get_param("Notification")
        subscribers = self._get_param("Subscribers")
        self.backend.create_notification(
            account_id=account_id,
            budget_name=budget_name,
            notification=notification,
            subscribers=subscribers,
        )
        return json.dumps(dict())

    def delete_notification(self):
        account_id = self._get_param("AccountId")
        budget_name = self._get_param("BudgetName")
        notification = self._get_param("Notification")
        self.backend.delete_notification(
            account_id=account_id, budget_name=budget_name, notification=notification
        )
        return json.dumps(dict())

    def describe_notifications_for_budget(self):
        account_id = self._get_param("AccountId")
        budget_name = self._get_param("BudgetName")
        notifications = self.backend.describe_notifications_for_budget(
            account_id=account_id, budget_name=budget_name
        )
        return json.dumps(dict(Notifications=notifications, NextToken=None))
