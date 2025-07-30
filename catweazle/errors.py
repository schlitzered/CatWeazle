from fastapi import HTTPException


class AuthenticationError(HTTPException):
    def __init__(self, msg="Invalid Username and Password"):
        super(AuthenticationError, self).__init__(status_code=401, detail=msg)


class DuplicateResource(HTTPException):
    def __init__(self):
        super(DuplicateResource, self).__init__(
            status_code=400, detail="Duplicate Resource"
        )


class ResourceNotFound(HTTPException):
    def __init__(self, details=None):
        if not details:
            details = "Resource not found"
        super(ResourceNotFound, self).__init__(status_code=404, detail=details)


class BackendError(HTTPException):
    def __init__(self):
        super(BackendError, self).__init__(
            status_code=500,
            detail="Internal Server Error: please contact administrator",
        )


class LdapResourceNotFound(HTTPException):
    def __init__(self):
        super(LdapResourceNotFound, self).__init__(
            status_code=400, detail="Ldap Resource not Found"
        )


class LdapInvalidDN(HTTPException):
    def __init__(self):
        super(LdapInvalidDN, self).__init__(status_code=400, detail="invalid ldap dn")


class LdapNoBackend(HTTPException):
    def __init__(self):
        super(LdapNoBackend, self).__init__(
            status_code=400,
            detail="No Ldap Backend configured, ldap operations not supported",
        )


class AdminError(HTTPException):
    def __init__(self):
        super(AdminError, self).__init__(
            status_code=403, detail="Admin Permissions required"
        )


class CredentialError(HTTPException):
    def __init__(self):
        super(CredentialError, self).__init__(
            status_code=403, detail="Invalid or no credentials"
        )


class SessionCredentialError(HTTPException):
    def __init__(self):
        super(SessionCredentialError, self).__init__(
            status_code=401, detail="No Session or API Credentials present"
        )


class PermError(HTTPException):
    def __init__(self, permission):
        super(PermError, self).__init__(
            status_code=403,
            detail=f"Permissions error, you are not granted {permission} on this resource",
        )


class HostNumRangeExceeded(HTTPException):
    def __init__(self, max_range):
        super(HostNumRangeExceeded, self).__init__(
            status_code=400,
            detail=f"Host number range exceeded for indicator {max_range}, "
            "please use a different indicator or remove existing hosts",
        )
