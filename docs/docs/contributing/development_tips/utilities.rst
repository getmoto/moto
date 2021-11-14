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
                # The collection of keys/attributes that should guarantee uniqueness for a given resource.
                # For most resources it will just be an ID, or ARN, which is always unique.
                # In order to know what is the last resource that we're sending back, an encoded version of these attributes is used as the NextToken.
                "page_ending_range_keys": ["start_date", "execution_arn"],
            },
            # another method that will use different configuration options
            "list_other_things": {
                ...
            },
        }

        # The decorator with the pagination logic
        @paginate(pagination_model=PAGINATION_MODEL)
        # Note that this method does not list the 'next_token'/'max_results'-arguments
        # The decorator uses them, but our logic doesn't need them
        def list_resources(self):
            # Note that we simply return all resources - the decorator takes care of all pagination magic
            return self.full_list_of_resources

