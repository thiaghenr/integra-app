"""Request-scoped correlation IDs, propagated via contextvars so any layer
(router, service, repository, DB event hook) can read them without the ID
being threaded through every function signature.

- trace_id: correlates a whole distributed operation. Reused from an inbound
  X-Trace-Id header when present (e.g. a call originating from the WhatsApp
  bot), otherwise generated fresh. May span multiple requests.
- request_id: always freshly generated per HTTP request, even if trace_id
  was inherited from upstream. Uniquely identifies this one request/response
  cycle within this service.
- span_id: one per logical unit of work within a request (e.g. one per DB
  query), so nested operations within a trace/request are distinguishable.
"""

import uuid
from contextvars import ContextVar

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
span_id_var: ContextVar[str | None] = ContextVar("span_id", default=None)
current_user_id_var: ContextVar[int | None] = ContextVar("current_user_id", default=None)
current_user_role_var: ContextVar[str | None] = ContextVar("current_user_role", default=None)


def new_id() -> str:
    return str(uuid.uuid4())


def get_trace_id() -> str | None:
    return trace_id_var.get()


def get_request_id() -> str | None:
    return request_id_var.get()


def get_span_id() -> str | None:
    return span_id_var.get()


def get_current_user_id() -> int | None:
    return current_user_id_var.get()


def get_current_user_role() -> str | None:
    return current_user_role_var.get()
