# REMURA v0.8.114 LAB — 17/11/2026 CET
"""Offline pull-stream rehearsal, no listening socket, Worker or real HTTP.
Caller is a synthetic bounded-read fixture; real asynchronous transport must
enforce timeout, cancellation and chunk bounds BEFORE allocation at the edge.
"""
from level_transport_http_lab_v1 import response
from level_transport_budget_lab_v1 import SharedAdapter
from level_transport_receiver_lab_v1 import MAX_BYTES

CHUNK=1024
MAX_READS=32

class StreamAdapter(SharedAdapter):
    def handle_stream(self,*,method,path,headers,peer,read):
        # Do not hold instance lock while invoking an untrusted/blocking reader.
        # Final persistent receiver transaction checks STOP again.
        with self._lock:
            if not self._enabled:return response("OFF")
            status=self._admit()
            if status is not None:return response(status)
            status,key,length=self._preflight(method,path,headers,peer)
            if status is not None:return response(status)
        if length==0 or not callable(read):return response("BAD_REQUEST")
        buf=bytearray()
        for _ in range(MAX_READS):
            limit=min(CHUNK,length-len(buf)+1)
            try:piece=read(limit)
            except Exception:return response("BAD_REQUEST")
            if type(piece) is not bytes:return response("BAD_REQUEST")
            if len(piece)>limit or len(buf)+len(piece)>MAX_BYTES:return response("SIZE")
            if not piece:
                if len(buf)!=length:return response("BAD_REQUEST")
                # Recheck local STOP before final receiver's transactional STOP.
                with self._lock:
                    if not self._enabled:return response("OFF")
                    return self._finish(key,length,bytes(buf))
            if len(buf)+len(piece)>length:return response("BAD_REQUEST")
            buf.extend(piece)
        return response("BAD_REQUEST")
