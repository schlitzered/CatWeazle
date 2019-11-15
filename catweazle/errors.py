__author__ = 'schlitzer'

__all__ = [
    'AdminError',
    'AlreadyAuthenticatedError',
    'AuthenticationError',
    'BackEndError',
    'BaseError',
    'CredentialError',
    'DuplicateResource',
    'FlowError',
    'ForemanConnError',
    'InvalidBody',
    'InvalidFields',
    'InvalidName',
    'InvalidPaginationLimit',
    'InvalidParameterValue',
    'InvalidSelectors',
    'InvalidSortCriteria',
    'InvalidUUID',
    'ModelError',
    'MongoConnError',
    'PeerReceiverCredentialError',
    'PermError',
    'ResourceNotFound',
    'ResourceInUse',
    'SessionError',
    'SessionCredentialError',
    'StaticPathDisabledError',
    'ValidationError'
]


class BaseError(Exception):
    def __init__(self, status, code, msg):
        super().__init__()
        self.status = status
        self.msg = msg
        self.code = code
        self.err_rsp = {'errors': [{
            "id": self.code,
            "details": self.msg,
            "title": self.msg
        }]}


class AAError(BaseError):
    def __init__(self, status=403, code=1000, msg=None):
        super().__init__(status, code, msg)


class ModelError(BaseError):
    def __init__(self, status=None, code=2000, msg=None):
        super().__init__(status, code, msg)


class ValidationError(BaseError):
    def __init__(self, status=None, code=3000, msg=None):
        super().__init__(status, code, msg)


class FeatureError(BaseError):
    def __init__(self, status=None, code=4000, msg=None):
        super().__init__(status, code, msg)


class BackEndError(BaseError):
    def __init__(self, status=None, code=5000, msg=None):
        super().__init__(status, code, msg)


class AuthenticationError(ModelError):
    def __init__(self):
        super().__init__(
            status=403,
            code=1001,
            msg="Invalid username or Password"
        )


class CredentialError(ModelError):
    def __init__(self):
        super().__init__(
            status=401,
            code=1002,
            msg="Invalid Credentials"
        )


class AlreadyAuthenticatedError(ModelError):
    def __init__(self):
        super().__init__(
            status=403,
            code=1003,
            msg="Already authenticated"
        )


class SessionError(ModelError):
    def __init__(self):
        super().__init__(
            status=403,
            code=1004,
            msg="Invalid or expired session"
        )


class PermError(ModelError):
    def __init__(self, msg):
        super().__init__(
            status=403,
            code=1005,
            msg=msg
        )


class SessionCredentialError(ModelError):
    def __init__(self):
        super().__init__(
            status=403,
            code=1006,
            msg="Neither valid Session or Credentials available"
        )


class AdminError(ModelError):
    def __init__(self):
        super().__init__(
            status=403,
            code=1007,
            msg="Root admin privilege needed for this resource"
        )


class PeerReceiverCredentialError(ModelError):
    def __init__(self):
        super().__init__(
            status=403,
            code=1008,
            msg="Receiver credentials needed for this resource"
        )


class ResourceNotFound(ModelError):
    def __init__(self, resource):
        super().__init__(
            status=404,
            code=2001,
            msg="No resource with ID {0} found".format(resource)
        )


class DuplicateResource(ModelError):
    def __init__(self, resource):
        super().__init__(
            status=400,
            code=2002,
            msg="Duplicate Resource: {0}".format(resource)
        )


class InvalidBody(ValidationError):
    def __init__(self, err):
        super().__init__(
            status=400,
            code=3001,
            msg="Invalid post body: {0}".format(err)
        )


class InvalidFields(ValidationError):
    def __init__(self, err):
        super().__init__(
            status=400,
            code=3003,
            msg="Invalid field selection: {0}".format(err)
        )


class InvalidSelectors(ValidationError):
    def __init__(self, err):
        super().__init__(
            status=400,
            code=3004,
            msg="Invalid selection: {0}".format(err)
        )


class InvalidPaginationLimit(ValidationError):
    def __init__(self, err):
        super().__init__(
            status=400,
            code=3005,
            msg="Invalid pagination limit, has to be one of: {0}".format(err)
        )


class InvalidSortCriteria(ValidationError):
    def __init__(self, err):
        super().__init__(
            status=400,
            code=3006,
            msg="Invalid sort criteria: {0}".format(err)
        )


class InvalidParameterValue(ValidationError):
    def __init__(self, err):
        super().__init__(
            status=400,
            code=3007,
            msg="Invalid parameter value: {0}".format(err)
        )


class InvalidUUID(ValidationError):
    def __init__(self, err):
        super().__init__(
            status=400,
            code=3008,
            msg="Invalid uuid: {0}".format(err)
        )


class InvalidName(ValidationError):
    def __init__(self, err):
        super().__init__(
            status=400,
            code=3009,
            msg="Invalid Name: {0}".format(err)
        )


class ResourceInUse(ValidationError):
    def __init__(self, err):
        super().__init__(
            status=400,
            code=3010,
            msg="Resource is still used: {0}".format(err)
        )


class FlowError(ValidationError):
    def __init__(self, err):
        super().__init__(
            status=400,
            code=3011,
            msg="Flow Error: {0}".format(err)
        )


class StaticPathDisabledError(FeatureError):
    def __init__(self):
        super().__init__(
            status=400,
            code=4002,
            msg="Static path feature is disabled"
        )


class MongoConnError(BackEndError):
    def __init__(self, err):
        super().__init__(
            status=500,
            code=5001,
            msg="MongoDB connection error: {0}".format(err)
        )


class RedisConnError(BackEndError):
    def __init__(self, err):
        super().__init__(
            status=500,
            code=5002,
            msg="Redis connection error: {0}".format(err)
        )


class ForemanConnError(BackEndError):
    def __init__(self, err):
        super().__init__(
            status=500,
            code=5003,
            msg="Foreman connection error: {0}".format(err)
        )
