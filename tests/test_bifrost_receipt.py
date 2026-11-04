"""Synthetic issuer receipts test protocol verification, not actual LLM weights."""
from pathlib import Path
import hashlib,hmac,http.server,json,secrets,sys,threading,unittest
ROOT=Path(__file__).resolve().parents[1]
for p in ['integrations/bifrost','tools/prompt-guard/src']:sys.path.insert(0,str(ROOT/p))
from model_receipt import ReceiptExpectation,ReceiptVerifier,ReceiptError,canonical
KEY=b'SYNTHETIC_RECEIPT_KEY_0000000000000'


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.expected=ReceiptExpectation.create(provider_id='synthetic-provider',model_revision='1'*64,runtime_revision='2'*64,route_policy_revision='3'*64,request=b'synthetic request',response=b'synthetic response')
        self.verifier=ReceiptVerifier({'synthetic-issuer':KEY},clock=lambda:1000)

    def signed(self,**changes):
        value={'version':1,'issuer':'synthetic-issuer','issued_at':999,'expires_at':1010,**self.expected.__dict__};value.update(changes)
        return json.dumps({'claims':value,'mac':hmac.new(KEY,canonical(value),hashlib.sha256).hexdigest()}).encode()

    def test_verified_claim_is_not_weights_attestation_or_admission(self):
        result=self.verifier.verify(self.signed(),self.expected)
        self.assertTrue(result.issuer_claim_verified);self.assertFalse(result.weights_attested);self.assertFalse(result.eligible)
        with self.assertRaises(ReceiptError):self.verifier.verify(self.signed(),self.expected)

    def test_signing_proxy_cannot_identify_opaque_loaded_state(self):
        # Real local HTTP; synthetic runtime states, NOT real LLM inference.
        # A signing proxy measures its approved disk/config state but has no
        # trusted observation of the hidden backend's serving handle.
        from client import LocalTransport
        configured_revision = '1'*64
        states = {'loaded_revision': configured_revision, 'observed': []}
        response = b'synthetic identical completion'
        class SigningProxy(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                raw = self.rfile.read(int(self.headers['Content-Length']))
                states['observed'].append(states['loaded_revision'])
                claim = {'version':1,'issuer':'synthetic-issuer','issued_at':999,'expires_at':1010,
                    'nonce':json.loads(raw)['nonce'],'provider_id':'synthetic-provider',
                    'model_revision':configured_revision,'runtime_revision':'2'*64,'route_policy_revision':'3'*64,
                    'request_sha256':hashlib.sha256(raw).hexdigest(),'response_sha256':hashlib.sha256(response).hexdigest()}
                receipt = json.dumps({'claims':claim,'mac':hmac.new(KEY,canonical(claim),hashlib.sha256).hexdigest()}).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(receipt)));self.end_headers();self.wfile.write(receipt)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),SigningProxy)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            transport=LocalTransport('http://127.0.0.1:'+str(server.server_port))
            for actual in [configured_revision,'4'*64]:
                states['loaded_revision']=actual
                nonce=secrets.token_hex(32);request=json.dumps({'nonce':nonce}).encode()
                expected=ReceiptExpectation(nonce,'synthetic-provider',configured_revision,'2'*64,'3'*64,
                    hashlib.sha256(request).hexdigest(),hashlib.sha256(response).hexdigest())
                verified=self.verifier.verify(transport(request),expected)
                self.assertTrue(verified.issuer_claim_verified)
                self.assertFalse(verified.weights_attested);self.assertFalse(verified.eligible)
            self.assertEqual(states['observed'],[configured_revision,'4'*64])
        finally:server.shutdown();server.server_close();thread.join()

    def test_unknown_issuer_fallback_revision_policy_and_body_change_fail(self):
        for change in [{'issuer':'unknown'},{'provider_id':'fallback'}, {'model_revision':'4'*64},
                       {'runtime_revision':'4'*64},{'route_policy_revision':'4'*64},
                       {'request_sha256':'4'*64},{'response_sha256':'4'*64},{'nonce':'4'*64}]:
            with self.subTest(change=change),self.assertRaises(ReceiptError):self.verifier.verify(self.signed(**change),self.expected)

    def test_expired_future_wrong_signature_and_unrecognized_fields_fail(self):
        for raw in [self.signed(expires_at=1000),self.signed(issued_at=1001),self.signed(expires_at=2000),
                    self.signed(weights_attested=True),self.signed(version=True),self.signed().replace(b'"mac": "',b'"mac": "0')]:
            with self.assertRaises(ReceiptError):self.verifier.verify(raw,self.expected)

    def test_unknown_revision_and_empty_trust_store_cannot_verify(self):
        broken=ReceiptExpectation(self.expected.nonce,'synthetic-provider','latest','2'*64,'3'*64,'4'*64,'5'*64)
        with self.assertRaises(ReceiptError):self.verifier.verify(self.signed(),broken)
        with self.assertRaises(ReceiptError):ReceiptVerifier({},clock=lambda:1000).verify(self.signed(),self.expected)
