# REMURA v0.8.114 LAB — 17/11/2026 CET
"""Pure HTTP-shaped synthetic adapter, NOT a web server or deployed Worker.
The caller supplies already bounded request bytes and a fixture peer identity.
No network binding, real IP trust, live capability, or authenticated clock.
"""
import re,hmac,threading
from level_local_probe_v1 import clock,need
from level_transport_receiver_lab_v1 import digest,MAX_BYTES
from level_transport_sqlite_lab_v1 import PersistentReceiver

ROUTE="/lab/levels/v1/"
PEER="SYNTHETIC_FIXTURE_PEER"
MAX_ATTEMPTS=48
WINDOW_MS=60000
WINDOW_LIMIT=20
MAPPING={"ACCEPTED_SYNTHETIC":201,"DUPLICATE":200,"CONFLICT":409,
         "CAPACITY":429,"OFF":503,"DENIED":403,"INVALID":400,"STORAGE_UNAVAILABLE":503}

def response(status):
    return {"http_status":MAPPING.get(status,{"RATE_LIMIT":429,"METHOD":405,
        "NOT_FOUND":404,"MEDIA_TYPE":415,"SIZE":413,"BAD_REQUEST":400,
        "CLOCK_UNAVAILABLE":503}.get(status,503)),
        "headers":{"Cache-Control":"no-store","Content-Type":"application/json",
                   "X-Content-Type-Options":"nosniff"},
        "body":{"status":status,"synthetic":True,"operational_signal":False}}

class Adapter:
    def __init__(self,receiver,*,key_hash,now,enabled=False,synthetic=False):
        need(synthetic is True and type(enabled) is bool and callable(now))
        need(type(receiver) is PersistentReceiver)
        need(type(key_hash) is str and re.fullmatch(r"[0-9a-f]{64}",key_hash) is not None)
        # Same synthetic enrollment at both gates; no caller-controlled identity mapping.
        need(hmac.compare_digest(key_hash,receiver._key))
        self._receiver=receiver;self._hash=key_hash;self._now=now;self._enabled=enabled
        self._lock=threading.Lock();self._attempts=0;self._window=None
        self._previous=None;self._window_count=0
    def stop(self):
        with self._lock:
            self._enabled=False
            self._receiver.stop()
    def _admit(self):
        # The fixed global limiter precedes path, credentials, body and storage.
        # All attempts count, no unbounded key/IP map; in-memory only.
        try:now=clock(self._now(),whole_second=False)
        except (ValueError,TypeError,OverflowError):return "CLOCK_UNAVAILABLE"
        if self._previous is not None and now<self._previous:return "CLOCK_UNAVAILABLE"
        self._previous=now
        window=now//WINDOW_MS
        if window!=self._window:self._window=window;self._window_count=0
        if self._attempts>=MAX_ATTEMPTS:return "RATE_LIMIT"
        self._attempts+=1
        if self._window_count>=WINDOW_LIMIT:return "RATE_LIMIT"
        self._window_count+=1
        return None
    def handle(self,*,method,path,headers,body,peer):
        with self._lock:
            if not self._enabled:return response("OFF")
            status=self._admit()
            if status is not None:return response(status)
            status,key,length=self._preflight(method,path,headers,peer)
            if status is not None:return response(status)
            return self._finish(key,length,body)
    def _preflight(self,method,path,headers,peer):
        if method!="POST":return "METHOD",None,None
        if type(path) is not str or not path.startswith(ROUTE):return "NOT_FOUND",None,None
        key=path[len(ROUTE):]
        if peer!=PEER or re.fullmatch(r"[0-9a-f]{64}",key) is None or not hmac.compare_digest(digest(key),self._hash):
            return "DENIED",None,None
        # Exact fixture header pairs, case-insensitive duplicate detection.
        if type(headers) is not list or len(headers)>16:return "BAD_REQUEST",None,None
        clean={}
        for pair in headers:
            if type(pair) is not tuple or len(pair)!=2:return "BAD_REQUEST",None,None
            name,value=pair
            if type(name) is not str or type(value) is not str or len(name)>80 or len(value)>256:return "BAD_REQUEST",None,None
            if not re.fullmatch(r"[A-Za-z0-9-]+",name) or any(ord(c)<32 or ord(c)>126 for c in value):return "BAD_REQUEST",None,None
            name=name.lower()
            if name in clean:return "BAD_REQUEST",None,None
            clean[name]=value
        if "transfer-encoding" in clean or "content-encoding" in clean:return "BAD_REQUEST",None,None
        if clean.get("content-type","").lower()!="application/json":return "MEDIA_TYPE",None,None
        length=clean.get("content-length","")
        if not re.fullmatch(r"[0-9]{1,6}",length):return "BAD_REQUEST",None,None
        if int(length)>MAX_BYTES:return "SIZE",None,None
        return None,key,int(length)
    def _finish(self,key,length,body):
        if int(length)>MAX_BYTES or (type(body) is bytes and len(body)>MAX_BYTES):return response("SIZE")
        if type(body) is not bytes or len(body)!=int(length) or not body:return response("BAD_REQUEST")
        try:raw=body.decode("utf-8",errors="strict")
        except UnicodeDecodeError:return response("BAD_REQUEST")
        result=self._receiver.receive(raw,capability=key)
        # First receipt, path, token, raw body, internal error never exposed.
        status=result.get("status")
        return response(status if status in MAPPING else "STORAGE_UNAVAILABLE")
