"""Synthetic application: intentionally vulnerable variants and safe controls."""
RECORDS = {'doc-a': {'owner': 'alice', 'text': 'synthetic-A'},
           'doc-b': {'owner': 'bob', 'text': 'synthetic-B'}}


def unguarded(actor, document):
    # Intentionally vulnerable: object ownership is ignored.
    return RECORDS[document]['text']


def guarded(actor, document):
    record = RECORDS[document]
    return record['text'] if record['owner'] == actor else None


def independent_guard(actor, document):
    # Intentionally vulnerable independent control: identity truthiness is not ownership.
    if actor:
        return RECORDS[document]['text']
    return None


def deny_all(actor, document):
    # Intentionally incorrect repair: allowed behavior also breaks.
    return None


VARIANTS = {
    'original': {'read': unguarded, 'export': unguarded, 'safe': guarded, 'independent': independent_guard},
    'partial': {'read': guarded, 'export': unguarded, 'safe': guarded, 'independent': independent_guard},
    'fixed': {'read': guarded, 'export': guarded, 'safe': guarded, 'independent': independent_guard},
    'cosmetic': {'read': unguarded, 'export': unguarded, 'safe': guarded, 'independent': independent_guard},
    'deny_all': {'read': deny_all, 'export': deny_all, 'safe': guarded, 'independent': independent_guard},
}


def observe():
    return {version: {route: {'unauthorized': handler('alice', 'doc-b'),
                             'authorized': handler('alice', 'doc-a')}
                      for route, handler in routes.items()}
            for version, routes in VARIANTS.items()}
