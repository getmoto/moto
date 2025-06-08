# KMS Policy Enforcement Implementation Rubrics

## Functional Requirements
- [x] Implement `evaluate_key_policy` method in the `Key` class
- [x] Add policy evaluation to all relevant KMS operations
- [x] Support exact action matches in policy evaluation (e.g., "kms:Encrypt")
- [x] Support wildcard action matches in policy evaluation (e.g., "kms:*")
- [x] Properly raise AccessDeniedException with informative messages
- [x] Handle both Allow and Deny effects in policy statements
- [x] Fix edge cases in re_encrypt method for invalid destination keys

## Code Quality
- [x] Code is well-structured and follows existing patterns
- [x] Error handling is robust and consistent
- [x] Method signatures and return types are consistent
- [x] Documentation is clear and comprehensive
- [x] Proper merge resolution of conflicting imports

## Testing
- [x] Tests successfully verify policy enforcement
- [x] Tests cover both positive and negative test cases
- [x] Tests use realistic policy documents

## Implementation Details
- [x] Policy document parsing is robust (handles JSON errors)
- [x] Support for both string and list action formats in policy
- [x] Prioritizes Deny effects over Allow effects (AWS standard)
- [x] Policy evaluation preserves backward compatibility 