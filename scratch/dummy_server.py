import logging
import sys
import asyncio
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.responses import JSONResponse

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(
    name="dummy_server",
)


@app.api_route(
    path="/{path:path}",
    methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "OPTIONS",
        "HEAD",
    ],
)
async def catch_all(
    request: Request,
    path: str,
):
    method = request.method
    headers = dict(request.headers)
    params = dict(request.query_params)
    body_bytes = await request.body()
    body_str = body_bytes.decode(
        encoding="utf-8",
        errors="replace",
    )

    logger.info(
        f"METHOD: {method}"
    )
    logger.info(
        f"PATH: {path}"
    )
    logger.info(
        f"HEADERS: {headers}"
    )
    logger.info(
        f"PARAMS: {params}"
    )
    logger.info(
        f"BODY: {body_str}"
    )

    delay_val = params.get("delay")
    if not delay_val:
        delay_val = headers.get("delay")
    if delay_val:
        try:
            delay = float(delay_val)
            await asyncio.sleep(
                delay=delay,
            )
        except ValueError:
            pass

    status_code = 200
    if method == "POST":
        status_code = 201

    override_val = params.get("answer_with")
    if not override_val:
        override_val = headers.get("answer-with")
    if not override_val:
        override_val = headers.get("answer_with")

    if override_val:
        try:
            status_code = int(override_val)
        except ValueError:
            pass

    return JSONResponse(
        content={
            "method": method,
            "path": path,
            "headers": headers,
            "params": params,
            "body": body_str,
        },
        status_code=status_code,
    )
