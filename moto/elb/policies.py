class Policy(object):
    def __init__(self, policy_type_name):
        self.policy_type_name = policy_type_name


class AppCookieStickinessPolicy(Policy):
    def __init__(self, policy_name, cookie_name):
        super().__init__(policy_type_name="AppCookieStickinessPolicy")
        self.policy_name = policy_name
        self.cookie_name = cookie_name


class LbCookieStickinessPolicy(Policy):
    def __init__(self, policy_name, cookie_expiration_period):
        super().__init__(policy_type_name="LbCookieStickinessPolicy")
        self.policy_name = policy_name
        self.cookie_expiration_period = cookie_expiration_period


class OtherPolicy(Policy):
    def __init__(self, policy_name, policy_type_name, policy_attrs):
        super().__init__(policy_type_name=policy_type_name)
        self.policy_name = policy_name
        self.attributes = policy_attrs or []
