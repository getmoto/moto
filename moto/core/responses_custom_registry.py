# This will only exist in responses >= 0.17
from responses import registries
from .custom_responses_mock import CallbackResponse, not_implemented_callback


class CustomRegistry(registries.FirstMatchRegistry):
    """
    Custom Registry that returns requests in an order that makes sense for Moto:
     - Implemented callbacks take precedence over non-implemented-callbacks
     - CallbackResponses are not discarded after first use - users can mock the same URL as often as they like
    """

    def find(self, request):
        found = []
        match_failed_reasons = []
        for response in self.registered:
            match_result, reason = response.matches(request)
            if match_result:
                found.append(response)
            else:
                match_failed_reasons.append(reason)

        # Look for implemented callbacks first
        implemented_matches = [
            m
            for m in found
            if type(m) is not CallbackResponse or m.callback != not_implemented_callback
        ]
        if implemented_matches:
            return implemented_matches[0], match_failed_reasons
        elif found:
            # We had matches, but all were of type not_implemented_callback
            return found[0], match_failed_reasons
        else:
            return None, match_failed_reasons
