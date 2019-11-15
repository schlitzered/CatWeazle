from uuid import uuid4
import json
import logging

from aiohttp.web import middleware, json_response
import aiotask_context as context
import jsonschema
import pymongo.errors

from catweazle.errors import BaseError
from catweazle.errors import InvalidBody
from catweazle.errors import MongoConnError


log = logging.getLogger('application')


@middleware
async def request_id(request, handler):
    _request_id = request.headers.get('X-Request-ID', None)
    if not _request_id:
        _request_id = str(uuid4())
        request['X-Request-ID'] = _request_id
        context.set('X-Request-ID', _request_id)
    response = await handler(request)
    response.headers['X-Request-ID'] = _request_id
    return response


@middleware
async def error_catcher(request, handler):
    _request_id = request['X-Request-ID']
    try:
        try:
            return await handler(request)
        except (jsonschema.exceptions.ValidationError, json.decoder.JSONDecodeError) as err:
            log.error('{0} received invalid JSON body {1}'.format(_request_id, err))
            raise InvalidBody(err)
        except pymongo.errors.ConnectionFailure as err:
            log.error('{0} error communicating with MongoDB: {1}'.format(_request_id, err))
            raise MongoConnError(err)
    except BaseError as err:
        return json_response(
            data=err.err_rsp,
            status=err.status
        )
