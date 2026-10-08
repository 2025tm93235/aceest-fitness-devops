"""Error types and JSON error handling for the API."""

from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """An error that is rendered as a JSON response with an HTTP status."""

    def __init__(
        self, message: str, status: int = 400, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"error": self.message}
        if self.details:
            body["details"] = self.details
        return body


def _wants_json() -> bool:
    return request.path.startswith("/api") or request.path == "/health"


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        return jsonify(err.to_dict()), err.status

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        if _wants_json():
            return jsonify({"error": err.description}), err.code
        return err
