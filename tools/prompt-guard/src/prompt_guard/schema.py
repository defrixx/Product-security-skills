"""Bounded, closed JSON contracts for output values and tool arguments.

Supported schema keywords are deliberately explicit. Unknown keywords are errors;
schemas cannot contain references, expressions, coercions or executable validators.
"""
import math
from .core import GuardError, require

TYPES = ('object', 'array', 'string', 'integer', 'number', 'boolean', 'null')


def finite(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def validate_schema(schema, depth=0):
    require(depth <= 16 and type(schema) is dict, 'schema_invalid')
    kind = schema.get('type')
    require(kind in TYPES, 'schema_invalid')
    common = {'type', 'enum'}
    extras = {'object': {'properties', 'required', 'additionalProperties'},
              'array': {'items', 'minItems', 'maxItems'},
              'string': {'minLength', 'maxLength'},
              'integer': {'minimum', 'maximum'}, 'number': {'minimum', 'maximum'}}.get(kind, set())
    require(set(schema) <= common | extras, 'schema_invalid')
    if kind == 'object':
        props, required = schema.get('properties'), schema.get('required', [])
        require(type(props) is dict and len(props) <= 128 and all(type(k) is str for k in props)
                and type(required) is list and all(type(k) is str and k in props for k in required)
                and len(set(required)) == len(required) and schema.get('additionalProperties') is False, 'schema_invalid')
        for value in props.values():
            validate_schema(value, depth + 1)
    if kind == 'array':
        require('items' in schema and 'maxItems' in schema, 'schema_invalid')
        validate_schema(schema['items'], depth + 1)
    if kind == 'string':
        require('maxLength' in schema, 'schema_invalid')
    for low, high in (('minItems', 'maxItems'), ('minLength', 'maxLength')):
        for key in (low, high):
            if key in schema:
                require(type(schema[key]) is int and 0 <= schema[key] <= 1048576, 'schema_invalid')
        require(schema.get(low, 0) <= schema.get(high, 1048576), 'schema_invalid')
    for key in ('minimum', 'maximum'):
        if key in schema:
            require(finite(schema[key]), 'schema_invalid')
    require(schema.get('minimum', -math.inf) <= schema.get('maximum', math.inf), 'schema_invalid')
    if 'enum' in schema:
        require(type(schema['enum']) is list and 0 < len(schema['enum']) <= 128, 'schema_invalid')
        for item in schema['enum']:
            try:
                validate_value(item, {k: v for k, v in schema.items() if k != 'enum'}, depth)
            except GuardError:
                raise GuardError('schema_invalid') from None


def validate_value(value, schema, depth=0):
    require(depth <= 16, 'output_schema_rejected')
    kind = schema['type']
    valid = {'object': type(value) is dict, 'array': type(value) is list,
             'string': type(value) is str, 'integer': type(value) is int,
             'number': type(value) in (int, float), 'boolean': type(value) is bool,
             'null': value is None}[kind]
    require(valid, 'output_schema_rejected')
    if 'enum' in schema:
        import json
        canonical = lambda v: json.dumps(v, sort_keys=True, allow_nan=False)
        require(any(canonical(value) == canonical(v) for v in schema['enum']), 'output_schema_rejected')
    if kind == 'object':
        require(set(value) <= set(schema['properties']) and set(schema.get('required', [])) <= set(value), 'output_schema_rejected')
        for key, item in value.items():
            validate_value(item, schema['properties'][key], depth + 1)
    elif kind == 'array':
        require(schema.get('minItems', 0) <= len(value) <= schema['maxItems'], 'output_schema_rejected')
        for item in value:
            validate_value(item, schema['items'], depth + 1)
    elif kind == 'string':
        require(schema.get('minLength', 0) <= len(value) <= schema['maxLength'], 'output_schema_rejected')
    elif kind in ('integer', 'number'):
        require(finite(value) and schema.get('minimum', -math.inf) <= value <= schema.get('maximum', math.inf), 'output_schema_rejected')
