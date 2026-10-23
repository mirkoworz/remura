#!/usr/bin/env python3
"""REMURA: interactive private setup of the read-only FP Markets cTrader account.

Run on the Oracle VPS as user remura, never in a public terminal or CI.
All OAuth secrets stay in memory or files under /opt/remura/private (0600).
"""
from __future__ import annotations

import getpass
import os
from pathlib import Path
import re
import sys
import tempfile

from ctrader_tokens import refresh,safe_write

PRIVATE=Path("/opt/remura/private")
ENV_PATH=PRIVATE/"remura.env"
TOKEN_PATH=PRIVATE/"ctrader-backup-tokens.json"
BACKUP_KEYS=("REMURA_CTRADER_BACKUP_ENABLED","CTRADER_BACKUP_ACCOUNT_ID","CTRADER_BACKUP_ENV")

def parse_environment(text):
    result={}
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key,value=line.split("=",1)
        key=key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",key):
            continue
        value=value.strip()
        if len(value)>=2 and value[0] in ("'",'"') and value[-1]==value[0]:
            value=value[1:-1]
        result[key]=value
    return result

def update_environment(text,settings):
    out=[]
    for line in text.splitlines():
        key=line.split("=",1)[0].strip() if "=" in line else ""
        if key not in BACKUP_KEYS:
            out.append(line)
    for key in BACKUP_KEYS:
        value=settings[key]
        if not re.fullmatch(r"[A-Za-z0-9_-]+",value):
            raise ValueError("Parametro privato non valido.")
        out.append(key+"="+value)
    return "\n".join(out)+"\n"

def account_options(accounts):
    options=[]
    for row in accounts:
        if not bool(getattr(row,"isLive",False)):
            continue
        broker=str(getattr(row,"brokerTitleShort","") or "Broker non indicato").strip()[:65]
        login=str(getattr(row,"traderLogin","") or "")
        options.append((row,broker,("••"+login[-3:]) if login else "N/D"))
    return options

def discover_accounts(client_id,client_secret,access_token):
    from ctrader_open_api import Client,TcpProtocol,EndPoints,Protobuf
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAApplicationAuthReq,ProtoOAApplicationAuthRes,
        ProtoOAGetAccountListByAccessTokenReq,ProtoOAGetAccountListByAccessTokenRes,
        ProtoOAErrorRes,
    )
    from twisted.internet import reactor

    client=Client(EndPoints.PROTOBUF_LIVE_HOST,EndPoints.PROTOBUF_PORT,TcpProtocol)
    state={"done":False,"failed":False,"items":None}
    def done(failed=False):
        if state["done"]:
            return
        state["done"]=True
        state["failed"]=failed
        if reactor.running:
            reactor.stop()
    def send(message):
        try:
            deferred=client.send(message)
            deferred.addErrback(lambda failure:done(True))
        except Exception:
            done(True)
    def connected(_):
        message=ProtoOAApplicationAuthReq()
        message.clientId=client_id
        message.clientSecret=client_secret
        send(message)
    def disconnected(_,reason):
        if not state["done"]:
            done(True)
    def received(_,message):
        if state["done"]:
            return
        try:
            payload=Protobuf.extract(message)
            if isinstance(payload,ProtoOAErrorRes):
                done(True)
            elif isinstance(payload,ProtoOAApplicationAuthRes):
                q=ProtoOAGetAccountListByAccessTokenReq()
                q.accessToken=access_token
                send(q)
            elif isinstance(payload,ProtoOAGetAccountListByAccessTokenRes):
                state["items"]=list(payload.ctidTraderAccount)
                done()
        except Exception:
            done(True)
    client.setConnectedCallback(connected)
    client.setDisconnectedCallback(disconnected)
    client.setMessageReceivedCallback(received)
    reactor.callLater(50,lambda:done(True))
    client.startService()
    reactor.run()
    if state["failed"] or state["items"] is None:
        raise RuntimeError("La connessione cTrader non ha restituito gli account autorizzati.")
    return state["items"]

def atomic_env(body):
    fd,tmp=tempfile.mkstemp(prefix=".backup-config-",dir=PRIVATE)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as file:
            file.write(body)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(tmp,0o600)
        os.replace(tmp,ENV_PATH)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def main():
    if os.geteuid()==0 or not sys.stdin.isatty():
        raise RuntimeError("Avvia come utente remura nella sessione SSH interattiva.")
    original=ENV_PATH.read_text(encoding="utf-8")
    env=parse_environment(original)
    cid=env.get("CTRADER_BACKUP_CLIENT_ID") or env.get("CTRADER_CLIENT_ID")
    secret=env.get("CTRADER_BACKUP_CLIENT_SECRET") or env.get("CTRADER_CLIENT_SECRET")
    if not cid or not secret:
        raise RuntimeError("Credenziali della tua applicazione cTrader non presenti nella VPS.")
    print("REMURA: connessione separata FP Markets LIVE, permesso Account info.")
    print("Il refresh token NON viene mostrato e non deve essere inviato in chat.")
    token=getpass.getpass("Incolla REFRESH TOKEN dal Playground (nascosto): ").strip()
    if not token or len(token)>4096:
        raise RuntimeError("Refresh token mancante o anomalo.")
    # Official cTrader HTTPS refresh rotates the supplied token and provides
    # an access token used only to discover permitted account IDs.
    rotated=refresh(cid,secret,token)
    token=""
    options=account_options(discover_accounts(cid,secret,rotated["accessToken"]))
    if not options:
        raise RuntimeError("Nessun conto LIVE autorizzato da questo token.")
    print("Conti LIVE autorizzati (ID interni nascosti):")
    for i,(_,broker,masked) in enumerate(options,1):
        print("  "+str(i)+". "+broker+" · login "+masked)
    selected=input("Numero del conto FP Markets: ").strip()
    if not selected.isdecimal() or not 1<=int(selected)<=len(options):
        raise RuntimeError("Scelta non valida, configurazione invariata.")
    account,broker,_=options[int(selected)-1]
    confirm=input("Broker selezionato: "+broker+". Digita FP per confermare: ").strip().upper()
    if confirm!="FP":
        raise RuntimeError("Configurazione annullata.")
    account_id=str(account.ctidTraderAccountId)
    if not account_id.isdecimal() or int(account_id)<=0:
        raise RuntimeError("ID account Open API non valido.")
    updated=update_environment(original,{
        "REMURA_CTRADER_BACKUP_ENABLED":"1",
        "CTRADER_BACKUP_ACCOUNT_ID":account_id,
        "CTRADER_BACKUP_ENV":"live",
    })
    safe_write(TOKEN_PATH,rotated)
    atomic_env(updated)
    print("OK: account FP Markets LIVE e token memorizzati sulla VPS privata.")
    print("Nessuna credenziale principale né storico modificato.")
    print("Ora riavvia il servizio remura-private per caricare la nuova configurazione.")

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,RuntimeError,ImportError) as exc:
        msg=str(exc) if isinstance(exc,RuntimeError) else "controlla connessione, SDK e permessi dei file."
        print("Configurazione interrotta: "+msg,file=sys.stderr)
        sys.exit(1)
