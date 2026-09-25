"""Real ASGI/Pydantic/SQLAlchemy exercise with synthetic data only."""
import importlib.metadata
import json
import os
from pathlib import Path
import tempfile
import unittest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

app = FastAPI()
engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
with engine.begin() as connection:
    connection.execute(text('CREATE TABLE records (name TEXT)'))
    connection.execute(text('INSERT INTO records VALUES (:name)'), [{'name': 'alpha'}, {'name': 'beta'}])
storage = tempfile.TemporaryDirectory(prefix="synthetic-import-")
writes = []

class Mutation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    label: str = Field(min_length=1, max_length=32)

class PublicRecord(BaseModel):
    name: str

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # No attacker-controlled input, field names, or custom validator context.
    return JSONResponse(status_code=422, content={'detail': 'Invalid request'})

@app.post('/records')
def mutate(payload: Mutation):
    writes.append(payload.label)
    return {'saved': True}

@app.get('/public', response_model=PublicRecord)
def public():
    return {'name': 'alpha', 'password': 'SYNTHETIC_RESPONSE_SECRET'}

@app.get('/lookup')
def lookup(name: str):
    with engine.connect() as connection:
        return list(connection.execute(text('SELECT name FROM records WHERE name=:name'), {'name': name}).scalars())

class ImportDocument(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    filename: str
    content: str = Field(max_length=1024)

@app.post('/import')
def import_document(payload: ImportDocument):
    name = payload.filename
    if not name or name in {'.', '..'} or any(c in name for c in ('/', '\\', ':', '\x00')):
        raise HTTPException(400, 'Invalid filename')
    # Fixed synthetic directory, exclusive creation; no traversal or overwrite.
    try:
        fd = os.open(str(Path(storage.name) / name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise HTTPException(409, 'Destination unavailable') from None
    with os.fdopen(fd, 'w') as output:
        output.write(payload.content)
    return {'saved': True}

class FrameworkTests(unittest.TestCase):
    def setUp(self):
        writes.clear()
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_schema_rejects_before_mutation(self):
        for body in [{'label': 'ok', 'role': 'admin'}, {'label': 123}, {'label': ''}, {'label': 'x'*33}]:
            self.assertEqual(self.client.post('/records', json=body).status_code, 422)
        self.assertEqual(writes, [])
        self.assertEqual(self.client.post('/records', json={'label': 'x'*32}).status_code, 200)
        self.assertEqual(writes, ['x'*32])

    def test_response_filters_secret(self):
        response = self.client.get('/public')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'name': 'alpha'})
        self.assertNotIn('SYNTHETIC_RESPONSE_SECRET', response.text)

    def test_real_sql_binding(self):
        self.assertEqual(self.client.get('/lookup', params={'name': "' OR 1=1 --"}).json(), [])
        self.assertEqual(self.client.get('/lookup', params={'name': 'alpha'}).json(), ['alpha'])

    def test_import_paths_and_symlink_before_write(self):
        with tempfile.TemporaryDirectory() as temp:
            outside = Path(temp) / 'sentinel'
            outside.write_text('unchanged')
            for name in ['../sentinel', str(outside), 'a/b', 'a\\b', 'C:relative', '..', '', '\x00']:
                response = self.client.post('/import', json={'filename': name, 'content': 'modified'})
                self.assertEqual(response.status_code, 400)
            link = Path(storage.name) / 'linked'
            link.symlink_to(outside)
            self.assertEqual(self.client.post('/import', json={'filename': 'linked', 'content': 'modified'}).status_code, 409)
            self.assertEqual(outside.read_text(), 'unchanged')
            self.assertEqual(self.client.post('/import', json={'filename': 'valid.txt', 'content': 'synthetic'}).status_code, 200)
            self.assertEqual((Path(storage.name) / 'valid.txt').read_text(), 'synthetic')
            self.assertEqual(self.client.post('/import', json={'filename': 'valid.txt', 'content': 'overwrite'}).status_code, 409)
            self.assertEqual((Path(storage.name) / 'valid.txt').read_text(), 'synthetic')

    def test_validation_response_omits_secret(self):
        canary = 'SYNTHETIC_VALIDATION_SECRET'
        response = self.client.post('/records', json={'label': 'ok', 'password': canary})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {'detail': 'Invalid request'})
        self.assertNotIn(canary, response.text)

if __name__ == '__main__':
    print(json.dumps({'versions': {name: importlib.metadata.version(name) for name in ['fastapi', 'pydantic', 'sqlalchemy', 'httpx', 'starlette']}}), flush=True)
    unittest.main(verbosity=2)
