"""Bounded local HTTP adapters. No proxies, redirects, retries or remote tools."""
from __future__ import annotations
import ipaddress
import json
import math
import multiprocessing
import urllib.error
import urllib.parse
import urllib.request

MAX_RESPONSE = 2 * 1024 * 1024

class EvaluationError(Exception):
    """Safe diagnostic code; never includes provider payloads or exception text."""


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite_json')
    def number(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError('nonfinite_json')
        return parsed
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant, parse_float=number)


def endpoint_url(endpoint, backend):
    """Accept numeric loopback only: no DNS rebinding or hostname resolution."""
    try:
        parsed = urllib.parse.urlsplit(endpoint)
        address = ipaddress.ip_address(parsed.hostname or '')
        if (parsed.scheme != 'http' or not address.is_loopback or parsed.username is not None
                or parsed.password is not None or parsed.path not in ('', '/')
                or parsed.query or parsed.fragment or parsed.port is None):
            raise ValueError()
    except ValueError:
        raise EvaluationError('invalid_local_endpoint') from None
    if backend not in ('lmstudio', 'ollama'):
        raise EvaluationError('invalid_backend')
    return endpoint.rstrip('/') + ('/v1/chat/completions' if backend == 'lmstudio' else '/api/chat')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EvaluationError('redirect_rejected')


def _worker(connection, url, payload, timeout):
    """Separate process lets parent enforce a whole-request deadline, even on trickle reads."""
    try:
        body = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode('utf-8') if payload is not None else None
        if body is not None and len(body) > 4 * 1024 * 1024:
            raise EvaluationError('request_too_large')
        request = urllib.request.Request(url, body, {'Content-Type': 'application/json'}, method='POST' if body is not None else 'GET')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=timeout) as response:
            if response.status != 200:
                raise EvaluationError('http_rejected')
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise EvaluationError('response_too_large')
            # Parse only in parent; the IPC payload is size-bounded bytes.
            connection.send(('ok', raw))
    except EvaluationError as error:
        connection.send(('error', str(error)))
    except urllib.error.HTTPError as error:
        code = {404: 'http_not_found', 405: 'http_method_rejected'}.get(error.code, 'http_rejected')
        connection.send(('error', code))
    except (TimeoutError, urllib.error.URLError, OSError):
        connection.send(('error', 'transport_failed'))
    except Exception:
        connection.send(('error', 'transport_failed'))
    finally:
        connection.close()


def post(url, payload, timeout):
    if not math.isfinite(timeout) or timeout <= 0:
        raise EvaluationError('deadline_exhausted')
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(child, url, payload, timeout), daemon=True)
    try:
        process.start()
        child.close()
        if not parent.poll(timeout):
            raise EvaluationError('request_timeout')
        try:
            status, value = parent.recv()
        except EOFError:
            raise EvaluationError('transport_failed') from None
        if status != 'ok':
            raise EvaluationError(value)
        try:
            result = strict_json(value.decode('utf-8'))
        except (ValueError, UnicodeError, RecursionError):
            raise EvaluationError('invalid_response_json') from None
        if not isinstance(result, dict):
            raise EvaluationError('invalid_response_shape')
        return result
    finally:
        child.close()
        parent.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)


def get(url, timeout):
    return post(url, None, timeout)


def payload(backend, model, messages, tools, temperature, max_tokens, seed):
    result = {'model': model, 'messages': messages, 'stream': False}
    if tools:
        result['tools'] = tools
    if backend == 'lmstudio':
        result.update(temperature=temperature, max_tokens=max_tokens, seed=seed)
    else:
        result['options'] = {'temperature': temperature, 'num_predict': max_tokens, 'seed': seed}
    return result


def decode(backend, response):
    """Normalize assistant envelope without persisting reasoning or arbitrary server metadata."""
    try:
        if backend == 'lmstudio':
            choices = response['choices']
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError()
            message = choices[0]['message']
            reason = choices[0]['finish_reason']
            complete = reason in ('stop', 'tool_calls')
        else:
            message = response['message']
            reason = response.get('done_reason')
            complete = response.get('done') is True and reason == 'stop'
        if not isinstance(message, dict) or message.get('role') != 'assistant':
            raise ValueError()
        content = message.get('content')
        if content is None and message.get('tool_calls'):
            content = ''
        if not isinstance(content, str):
            raise ValueError()
        content.encode('utf-8', errors='strict')
        calls = message.get('tool_calls', [])
        if not isinstance(calls, list) or len(calls) > 16:
            raise ValueError()
        normalized = {'role': 'assistant', 'content': content}
        if calls:
            normalized['tool_calls'] = calls
        return normalized, complete
    except (KeyError, TypeError, ValueError, UnicodeError):
        raise EvaluationError('invalid_response_shape') from None
