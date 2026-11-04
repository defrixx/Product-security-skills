"""Verify first-party completion claims; never equate signatures with weights.

Issuer keys are independently provisioned application configuration. Ordinary
LM Studio/Bifrost responses do not implement this protocol. Receipt verification
never establishes actual loaded weights or a Model Security Eval admission permit.
"""
from dataclasses import dataclass,field
import hashlib,hmac,secrets,threading,time
from types import MappingProxyType
from prompt_guard.core import decode
import json,re
HEX=re.compile(r'[0-9a-f]{64}\Z');ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z')


class ReceiptError(Exception):pass


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


@dataclass(frozen=True)
class ReceiptExpectation:
    nonce: str
    provider_id: str
    model_revision: str
    runtime_revision: str
    route_policy_revision: str
    request_sha256: str
    response_sha256: str

    @classmethod
    def create(cls,*,provider_id,model_revision,runtime_revision,route_policy_revision,request,response):
        return cls(secrets.token_hex(32),provider_id,model_revision,runtime_revision,route_policy_revision,
                   hashlib.sha256(request).hexdigest(),hashlib.sha256(response).hexdigest())


@dataclass(frozen=True)
class VerifiedReceipt:
    issuer: str
    provider_id: str
    model_revision: str
    issuer_claim_verified: bool=field(default=True,init=False)
    weights_attested: bool=field(default=False,init=False)
    eligible: bool=field(default=False,init=False)


class ReceiptVerifier:
    def __init__(self,keys,*,clock=time.time,max_lifetime=60):
        if (type(keys) is not dict or any(type(k) is not str or not ID.fullmatch(k) or type(v) is not bytes
            or not 32<=len(v)<=64 for k,v in keys.items()) or not callable(clock)
            or type(max_lifetime) is not int or not 1<=max_lifetime<=300):raise ReceiptError('receipt_config_invalid')
        self._keys=MappingProxyType(dict(keys));self._clock=clock;self._lifetime=max_lifetime
        self._used={};self._lock=threading.Lock()

    def verify(self,raw,expected):
        try:
            if type(expected) is not ReceiptExpectation:raise ReceiptError('receipt_expectation_invalid')
            if not ID.fullmatch(expected.provider_id):raise ReceiptError('receipt_expectation_invalid')
            for key in ('nonce','model_revision','runtime_revision','route_policy_revision','request_sha256','response_sha256'):
                value=getattr(expected,key)
                if type(value) is not str or not HEX.fullmatch(value):raise ReceiptError('receipt_expectation_invalid')
            value=decode(raw,8192)
            if type(value) is not dict or set(value)!={'claims','mac'}:raise ReceiptError('receipt_invalid')
            claim=value['claims'];mac=value['mac']
            fields={'version','issuer','provider_id','model_revision','runtime_revision','route_policy_revision',
                    'request_sha256','response_sha256','nonce','issued_at','expires_at'}
            if type(claim) is not dict or set(claim)!=fields or type(claim['version']) is not int or claim['version']!=1:raise ReceiptError('receipt_invalid')
            issuer=claim['issuer']
            if type(issuer) is not str or issuer not in self._keys:raise ReceiptError('receipt_issuer_unknown')
            if type(mac) is not str or not HEX.fullmatch(mac):raise ReceiptError('receipt_invalid')
            trusted=hmac.new(self._keys[issuer],canonical(claim),hashlib.sha256).hexdigest()
            if not hmac.compare_digest(mac,trusted):raise ReceiptError('receipt_signature_invalid')
            for key in ('provider_id','model_revision','runtime_revision','route_policy_revision','request_sha256','response_sha256','nonce'):
                if claim[key]!=getattr(expected,key):raise ReceiptError('receipt_binding_mismatch')
            now=self._clock();issued,expires=claim['issued_at'],claim['expires_at']
            if (type(issued) is not int or type(expires) is not int or not issued<=now<expires
                    or not 0<expires-issued<=self._lifetime):raise ReceiptError('receipt_expired_or_future')
            with self._lock:
                self._used={nonce:expiry for nonce,expiry in self._used.items() if expiry>now}
                if expected.nonce in self._used:raise ReceiptError('receipt_replay')
                if len(self._used)>=4096:raise ReceiptError('receipt_resource_limit')
                self._used[expected.nonce]=expires
            # A MAC proves possession of a trusted issuer key and bound claims,
            # not that an opaque backend actually loaded those weights. There is
            # deliberately no path from this object to eligible=True.
            return VerifiedReceipt(issuer,expected.provider_id,expected.model_revision)
        except ReceiptError:raise
        except Exception:raise ReceiptError('receipt_invalid') from None
