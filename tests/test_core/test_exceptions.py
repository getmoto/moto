from moto.core.exceptions import ServiceException


class TestServiceException:
    class ServiceError(ServiceException):
        code = "ExceptionCode"
        message = "default message"

    def test_exception_string(self) -> None:
        exc = TestServiceException.ServiceError()
        assert str(exc) == "ExceptionCode: default message"

    def test_formatted_exception_message(self) -> None:
        class FormattedException(ServiceException):
            message = "The {resource_type} resource {resource_id} was not found!"

        exc = FormattedException(resource_type="DBCluster", resource_id="cluster-id")
        assert exc.message == "The DBCluster resource cluster-id was not found!"

    def test_override_exception_message(self) -> None:
        exc = TestServiceException.ServiceError("Override message")
        assert str(exc) == "ExceptionCode: Override message"

    def test_override_exception_message_and_code(self) -> None:
        exc = TestServiceException.ServiceError("OverrideCode", "Override message")
        assert str(exc) == "OverrideCode: Override message"
