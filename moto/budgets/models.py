from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from moto.core import BaseBackend, BaseModel
from moto.core.utils import unix_time

from .exceptions import BudgetMissingLimit, DuplicateRecordException, NotFoundException


class Notification(BaseModel):
    def __init__(self, details, subscribers):
        self.details = details
        self.subscribers = subscribers


class Budget(BaseModel):
    def __init__(self, budget, notifications):
        if "BudgetLimit" not in budget and "PlannedBudgetLimits" not in budget:
            raise BudgetMissingLimit()
        # Storing the budget as a Dict for now - if we need more control, we can always read/write it back
        self.budget = budget
        self.notifications = [
            Notification(details=x["Notification"], subscribers=x["Subscribers"])
            for x in notifications
        ]
        self.budget["LastUpdatedTime"] = unix_time()
        if "TimePeriod" not in self.budget:
            first_day_of_month = datetime.now().replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            self.budget["TimePeriod"] = {
                "Start": unix_time(first_day_of_month),
                "End": 3706473600,  # "2087-06-15T00:00:00+00:00"
            }

    def to_dict(self):
        cp = deepcopy(self.budget)
        if "CalculatedSpend" not in cp:
            cp["CalculatedSpend"] = {
                "ActualSpend": {"Amount": "0", "Unit": "USD"},
                "ForecastedSpend": {"Amount": "0", "Unit": "USD"},
            }
        if self.budget["BudgetType"] == "COST" and "CostTypes" not in cp:
            cp["CostTypes"] = {
                "IncludeCredit": True,
                "IncludeDiscount": True,
                "IncludeOtherSubscription": True,
                "IncludeRecurring": True,
                "IncludeRefund": True,
                "IncludeSubscription": True,
                "IncludeSupport": True,
                "IncludeTax": True,
                "IncludeUpfront": True,
                "UseAmortized": False,
                "UseBlended": False,
            }
        return cp

    def add_notification(self, details, subscribers):
        self.notifications.append(Notification(details, subscribers))

    def delete_notification(self, details):
        self.notifications = [n for n in self.notifications if n.details != details]

    def get_notifications(self):
        return [n.details for n in self.notifications]


class BudgetsBackend(BaseBackend):
    """Implementation of Budgets APIs."""

    def __init__(self):
        # {"account_id": {"budget_name": Budget}}
        self.budgets = defaultdict(dict)

    def create_budget(self, account_id, budget, notifications):
        budget_name = budget["BudgetName"]
        if budget_name in self.budgets[account_id]:
            raise DuplicateRecordException(
                record_type="budget", record_name=budget_name
            )
        self.budgets[account_id][budget_name] = Budget(budget, notifications)

    def describe_budget(self, account_id, budget_name):
        if budget_name not in self.budgets[account_id]:
            raise NotFoundException(
                f"Unable to get budget: {budget_name} - the budget doesn't exist."
            )
        return self.budgets[account_id][budget_name].to_dict()

    def describe_budgets(self, account_id):
        """
        Pagination is not yet implemented
        """
        return [budget.to_dict() for budget in self.budgets[account_id].values()]

    def delete_budget(self, account_id, budget_name):
        if budget_name not in self.budgets[account_id]:
            msg = f"Unable to delete budget: {budget_name} - the budget doesn't exist. Try creating it first. "
            raise NotFoundException(msg)
        self.budgets[account_id].pop(budget_name)

    def create_notification(self, account_id, budget_name, notification, subscribers):
        if budget_name not in self.budgets[account_id]:
            raise NotFoundException(
                "Unable to create notification - the budget doesn't exist."
            )
        self.budgets[account_id][budget_name].add_notification(
            details=notification, subscribers=subscribers
        )

    def delete_notification(self, account_id, budget_name, notification):
        if budget_name not in self.budgets[account_id]:
            raise NotFoundException(
                "Unable to delete notification - the budget doesn't exist."
            )
        self.budgets[account_id][budget_name].delete_notification(details=notification)

    def describe_notifications_for_budget(self, account_id, budget_name):
        """
        Pagination has not yet been implemented
        """
        return self.budgets[account_id][budget_name].get_notifications()


budgets_backend = BudgetsBackend()
