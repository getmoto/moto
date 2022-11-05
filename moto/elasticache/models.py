from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict

from .exceptions import UserAlreadyExists, UserNotFound


class User(BaseModel):
    def __init__(
        self,
        account_id,
        region,
        user_id,
        user_name,
        access_string,
        engine,
        no_password_required,
        passwords=None,
    ):
        self.id = user_id
        self.name = user_name
        self.engine = engine
        self.passwords = passwords or []
        self.access_string = access_string
        self.no_password_required = no_password_required
        self.status = "active"
        self.minimum_engine_version = "6.0"
        self.usergroupids = []
        self.region = region
        self.arn = f"arn:aws:elasticache:{self.region}:{account_id}:user:{self.id}"


class ElastiCacheBackend(BaseBackend):
    """Implementation of ElastiCache APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.users = dict()
        self.users["default"] = User(
            account_id=self.account_id,
            region=self.region_name,
            user_id="default",
            user_name="default",
            engine="redis",
            access_string="on ~* +@all",
            no_password_required=True,
        )

    def create_user(
        self, user_id, user_name, engine, passwords, access_string, no_password_required
    ):
        if user_id in self.users:
            raise UserAlreadyExists
        user = User(
            account_id=self.account_id,
            region=self.region_name,
            user_id=user_id,
            user_name=user_name,
            engine=engine,
            passwords=passwords,
            access_string=access_string,
            no_password_required=no_password_required,
        )
        self.users[user_id] = user
        return user

    def delete_user(self, user_id):
        if user_id in self.users:
            user = self.users[user_id]
            if user.status == "active":
                user.status = "deleting"
            return user
        raise UserNotFound(user_id)

    def describe_users(self, user_id):
        """
        Only the `user_id` parameter is currently supported.
        Pagination is not yet implemented.
        """
        if user_id:
            if user_id in self.users:
                user = self.users[user_id]
                if user.status == "deleting":
                    self.users.pop(user_id)
                return [user]
            else:
                raise UserNotFound(user_id)
        return self.users.values()


elasticache_backends = BackendDict(ElastiCacheBackend, "elasticache")
