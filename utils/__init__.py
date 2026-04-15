from __future__ import annotations

from flask import flash, jsonify, redirect, request, url_for


def wants_json_response() -> bool:
    requested_with = (request.headers.get('X-Requested-With') or '').lower()
    if requested_with == 'xmlhttprequest':
        return True

    accept = request.accept_mimetypes
    if not accept:
        return False

    json_q = accept['application/json']
    html_q = accept['text/html']
    if accept.accept_json and json_q >= html_q:
        return True
    return False


def api_error_response(message: str, redirect_endpoint: str, *, status: int = 400, category: str = 'danger'):
    if wants_json_response():
        return jsonify({'message': message}), status
    flash(message, category)
    return redirect(url_for(redirect_endpoint))


__all__ = ['api_error_response', 'wants_json_response']
