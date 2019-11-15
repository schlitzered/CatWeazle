CHECK_CONFIG_MAIN = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "domain_suffix",
        "host",
        "port",
    ],
    "properties": {
        "domain_suffix": {
            "type": "string",
        },
        "dry_run": {
            "type": "boolean",
        },
        "host": {
            "type": "string",
        },
        "indicator_regex": {
            "type": "string",
        },
        "port": {
            "type": "integer",
            "maximum": 65535,
            "minimum": 1
        },
    }
}

CHECK_CONFIG_MONGOPOOL = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "hosts",
        "db"
    ],
    "optional": [
        "pass",
        "user"
    ],
    "properties": {
        "hosts": {
            "type": "string",
        },
        "db": {
            "type": "string",
        },
        "pass": {
            "type": "string",
        },
        "user": {
            "type": "string",
        },
    }
}

CHECK_CONFIG_MONGOCOLL = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "coll",
        "pool"
    ],
    "properties": {
        "coll": {
            "type": "string",
        },
        "pool": {
            "type": "string",
        }
    }
}

CHECK_CONFIG_REDISPOOL = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "host": {
            "type": "string",
        },
        "port": {
            "type": "integer",
        },
        "pass": {
            "type": "string",
        },
    }
}

