# This will only exist in responses >= 0.17
import responses
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Optional
from .custom_responses_mock import CallbackResponse, not_implemented_callback


class CustomRegistry(responses.registries.FirstMatchRegistry):
    """
    Custom Registry that returns requests in an order that makes sense for Moto:
     - Implemented callbacks take precedence over non-implemented-callbacks
     - CallbackResponses are not discarded after first use - users can mock the same URL as often as they like
     - CallbackResponses are persisted in a dictionary, with the request-method as key
       This reduces the number of possible responses that we need to search
    """

    def __init__(self) -> None:
        self._registered: Dict[str, List[responses.BaseResponse]] = defaultdict(list)

    @property
    def registered(self) -> List[responses.BaseResponse]:
        res = []
        for resps in self._registered.values():
            res += resps
        return res

    def add(self, response: responses.BaseResponse) -> responses.BaseResponse:
        if response not in self._registered[response.method]:
            self._registered[response.method].append(response)
        return response

    def reset(self) -> None:
        self._registered.clear()

    def find(self, request: Any) -> Tuple[Optional[responses.BaseResponse], List[str]]:
        # We don't have to search through all possible methods - only the ones registered for this particular method
        all_possibles = (
            responses._default_mock._registry.registered
            + self._registered[request.method]
        )
        found = []
        match_failed_reasons = []
        for response in all_possibles:
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
