"""Test helpers"""
import json
from http import HTTPStatus
from types import SimpleNamespace
from typing import List, Mapping, Optional, Union

from aiohttp import (
    ClientSession,
    TraceConfig,
    TraceRequestChunkSentParams,
    TraceRequestEndParams,
    web,
)

from .const import TEST_V4_PATH


async def create_session(
    aiohttp_client,
    file_name: Union[str, List[str]],
    *,
    headers: Optional[Mapping[str, str]] = None,
    status: HTTPStatus = HTTPStatus.OK,
):
    """Create aiohttp session that returns results from a file"""

    ns = SimpleNamespace(
        file_names=[file_name] if isinstance(file_name, str) else file_name,
        index=0,
        headers=headers,
        status=status,
    )

    async def response_handler(request):  # pylint: disable=unused-argument
        if ns.index >= len(ns.file_names):
            return None  # it's too late in the pipe to generate connection exception

        file_name = ns.file_names[ns.index]
        ns.index += 1

        with open(f"tests/fixtures/{file_name}", "r", encoding="utf8") as file:
            text = file.read()

        return web.json_response(text=text, headers=ns.headers, status=ns.status)

    app = web.Application()
    app.router.add_post(TEST_V4_PATH, response_handler)
    return await aiohttp_client(app)


def create_trace_config() -> TraceConfig:
    """Create 'TraceConfig' for tracing aiohttp responses"""

    async def on_request_chunk_sent(
        session: ClientSession,  # pylint: disable=unused-argument
        trace_config_ctx: SimpleNamespace,
        params: TraceRequestChunkSentParams,
    ):
        trace_config_ctx.request_body = params.chunk

    async def on_request_end(
        session: ClientSession,  # pylint: disable=unused-argument
        trace_config_ctx: SimpleNamespace,
        params: TraceRequestEndParams,
    ):
        print("Request:")
        print(params.url)
        for k, v in params.headers.items():
            print(f"  {k}: {v}")
        if trace_config_ctx.request_body:
            print(trace_config_ctx.request_body)
        print()
        print("Response:")
        for k, v in sorted(params.response.headers.items()):
            print(f"  {k}: {v}")
        resp = await params.response.json()
        print(json.dumps(resp, indent=2))
        print()

    trace_config = TraceConfig()
    trace_config.on_request_chunk_sent.append(on_request_chunk_sent)
    trace_config.on_request_end.append(on_request_end)
    return trace_config
