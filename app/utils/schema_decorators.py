from __future__ import annotations
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Union
from flask import request, jsonify
from marshmallow import Schema, ValidationError

Jsonable = Union[dict, list, str, int, float, bool, None]

def use_schema(
        schema_class: type[Schema],
        *,
        arg_name: str = "payload",
        many: bool = False,
        load_kwargs: Optional[dict] = None,
        error_status: int = 400,
        require_json: bool = True,
) -> Callable:
    load_kwargs = load_kwargs or {}
    def decorator(fn:Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if require_json and not request.is_json:
                return jsonify(error="Expected application/json"), 415
            
            raw = request.get_json(silent=True)
            if raw is None:
                raw = [] if many else {}

            if many and not isinstance(raw,list):
                return jsonify(error="Expected a JSON array"), error_status
            if not many and isinstance(raw,list):
                return jsonify(error="Expected a JSON object"), error_status
            
            try:
                data = schema_class(many=many).load(raw, **load_kwargs)
            except ValidationError as e:
                return jsonify(error=e.messages), error_status
            
            kwargs[arg_name] = data
            return fn(*args, **kwargs)
        return wrapper
    return decorator

