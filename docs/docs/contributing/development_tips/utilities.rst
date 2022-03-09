.. _contributing utilities:

=============================
Utilities
=============================

Tagging Service
******************************

A dedicated TaggingService exists in `moto.utilities`, to help with storing/retrieving tags for resources.

Not all services use it yet, but contributors are encouraged to  use the TaggingService for all new features.


Paginator
***********

When requesting a list of resources, almost all AWS services use pagination to stagger the response.
Moto provides a utility class to automatically paginate a response, without having to manually write the logic.

There are three components that make this work:

 #. The Responses-method will call the backend with a max_result/next_token parameter
 #. The backend-method has a plain method that's decorated with `@paginate`
 #. A configuration model is supplied to the decorator that contains all the details.

See the below example how it works in practice:

.. sourcecode:: python

    class MyResponse(BaseResponse):

        # The Response-class looks like any other - read the input parameters, and call the backend to retrieve the resources
        def list_resources():
            max_results = 100
            next_token = self._get_param("NextToken")
            # Note that we're getting both the results and the next_token
            # The decorator in the backend returns this tuple
            paged_results, next_token = self.backend.list_resources(
                max_results=max_results, next_token=next_token
            )
            ...

    from moto.utilities.paginator import paginate
    class MyBackend(BaseBackend):

        # The model that contains the configuration required for the paginator
        PAGINATION_MODEL = {
            # key = name of the method in the backend
            "list_resources": {
                #
                # name of the kwarg that contains the next token, which should be passed to the backend
                # backend.list_resources(next_token=..)
                "input_token": "next_token",
                #
                # name of the kwarg that contains the max number of results, which should be passed to the backend
                "limit_key": "max_results",
                #
                # The default limit of the above parameter is not provided
                "limit_default": 100,
                #
                # One or more attributes  that guarantee uniqueness for a given resource.
                # For most resources it will just be an ID, or ARN, which is always unique.
                # An encoded version of these attributes is used as the NextToken.
                "unique_attribute": "arn",
                # Provide a list if only a combination of attributes is guaranteed to be unique
                "unique_attribute": ["start_date", "execution_arn"],
                #
                # By default, an exception will be thrown if the user-provided next_token is invalid
                "fail_on_invalid_token": True  # Default value - no need to specify this
                # This can be customized to:
                #   - silently fail, and just return an empty list
                "fail_on_invalid_token": False,
                #   - throw a custom exception, by providing an exception class
                #     The paginator will `raise CustomException()` or `raise CustomException(invalid_token)`
                "fail_on_invalid_token": CustomException
            },
            # another method that will use different configuration options
            "list_other_things": {
                ...
            },
        }

        # The decorator with the pagination logic
        @paginate(pagination_model=PAGINATION_MODEL)
        # Note that this method does not have the 'next_token'/'max_results'-arguments
        def list_resources(self):
            # Note that we simply return all resources - the decorator takes care of all pagination magic
            return self.full_list_of_resources

        @paginate(pagination_model=PAGINATION_MODEL)
        # If we do need the 'next_token'/'max_results'-arguments, just add them to the function
        # The decorator will only pass them along if required
        def list_other_things(self, max_results=None):
            if max_results == "42":
                # Custom validation magic
                pass
            return self.full_list_of_resources

