#!/usr/bin/env python3
"""Choose an authorised cTrader Demo account privately; no trading or orders.

Open API ctidTraderAccountId is NOT the same as the broker's visible login.
Only writes CTRADER_ACCOUNT_ID and CTRADER_ENV=demo to private remura.env after
explicit local selection. No tokens, secrets or full IDs are printed.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile

from ctrader_tokens import access_token

ENV_FILE = Path('/opt/remura/private/remura.env')
DB_FILE = Path('/opt/remura/private/remura-prices.sqlite3')


def read_environment(path):
    data = {}
    for line in Path(path).read_text('utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*', key):
            continue
        if key in data:
            raise ValueError('Configurazione duplicata: ' + key)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        data[key] = value
    return data


def save_demo_selection(path, account_id):
    """Atomic, restrictive update preserving existing credentials byte-for-byte."""
    if not isinstance(account_id, int) or not 0 < account_id < (1 << 64):
        raise ValueError('Identificativo conto non valido')
    target = Path(path)
    if not target.is_file() or target.is_symlink():
        raise ValueError('File di configurazione non valido')
    if target.stat().st_uid != os.geteuid():
        raise ValueError('Eseguire con utente remura')
    original = target.read_text('utf-8')
    lines = original.splitlines(keepends=True)
    updated = []
    found = set()
    for row in lines:
        k = row.split('=', 1)[0].strip() if '=' in row and not row.lstrip().startswith('#') else ''
        if k in ('CTRADER_ACCOUNT_ID', 'CTRADER_ENV'):
            if k in found:
                raise ValueError('Configurazione duplicata: ' + k)
            found.add(k)
            updated.append(k + '=' + (str(account_id) if k == 'CTRADER_ACCOUNT_ID' else 'demo') + '\n')
        else:
            updated.append(row)
    for k, v in [('CTRADER_ACCOUNT_ID', str(account_id)), ('CTRADER_ENV', 'demo')]:
        if k not in found:
            if updated and not updated[-1].endswith('\n'):
                updated.append('\n')
            updated.append(k + '=' + v + '\n')
    fd, temp_name = tempfile.mkstemp(prefix='.remura-account-', dir=target.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(''.join(updated))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
        os.chmod(target, 0o600)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def demo_labels(accounts):
    """Return UI labels only, never the ctidTraderAccountId or full login."""
    result = []
    for item in accounts:
        if bool(item.isLive):
            continue
        aid = int(item.ctidTraderAccountId)
        if not 0 < aid < (1 << 64):
            continue
        broker = str(getattr(item, 'brokerTitleShort', '') or 'Broker').strip()
        broker = re.sub(r'[^\w .-]', '', broker, flags=re.UNICODE)[:36] or 'Broker'
        login = str(getattr(item, 'traderLogin', '') or '')
        ending = (login[-3:] if login.isdecimal() else 'N/D')
        result.append((aid, broker, ending))
    return result


def get_authorized_accounts(env, token):
    """Request authorised account metadata; never request balances or orders."""
    from ctrader_open_api import Client, TcpProtocol, EndPoints, Protobuf
    from ctrader_open_api.messages.OpenApiMessages_pb2 import (
        ProtoOAApplicationAuthReq, ProtoOAApplicationAuthRes,
        ProtoOAGetAccountListByAccessTokenReq, ProtoOAGetAccountListByAccessTokenRes,
        ProtoOAErrorRes,
    )
    from twisted.internet import reactor

    result = {'accounts': None, 'error': None, 'done': False}
    client = Client(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)

    def finish(error=None):
        if result['done']:
            return
        result['done'] = True
        if error:
            result['error'] = error
        if reactor.running:
            reactor.stop()

    def send(msg):
        try:
            deferred = client.send(msg)
            deferred.addErrback(lambda failure: finish('Richiesta cTrader rifiutata'))
        except Exception:
            finish('Errore comunicazione cTrader')

    def connected(_):
        msg = ProtoOAApplicationAuthReq()
        msg.clientId = env['CTRADER_CLIENT_ID']
        msg.clientSecret = env['CTRADER_CLIENT_SECRET']
        send(msg)

    def received(_, msg):
        if result['done']:
            return
        try:
            payload = Protobuf.extract(msg)
            if isinstance(payload, ProtoOAErrorRes):
                finish('Autenticazione Open API rifiutata')
            elif isinstance(payload, ProtoOAApplicationAuthRes):
                req = ProtoOAGetAccountListByAccessTokenReq()
                req.accessToken = token
                send(req)
            elif isinstance(payload, ProtoOAGetAccountListByAccessTokenRes):
                result['accounts'] = list(payload.ctidTraderAccount)
                finish()
        except Exception:
            finish('Risposta API non valida')

    client.setConnectedCallback(connected)
    client.setDisconnectedCallback(lambda *_: finish('Connessione cTrader interrotta'))
    client.setMessageReceivedCallback(received)
    reactor.callLater(35, lambda: finish('Timeout cTrader: riprovare più tardi'))
    client.startService()
    reactor.run()
    if result['error']:
        raise RuntimeError(result['error'])
    if result['accounts'] is None:
        raise RuntimeError('Nessun elenco conti ricevuto')
    return result['accounts']


def main():
    try:
        env = read_environment(ENV_FILE)
        if not env.get('CTRADER_CLIENT_ID') or not env.get('CTRADER_CLIENT_SECRET'):
            print('Mancano le credenziali cTrader nel file privato.')
            return 1
        token = access_token(DB_FILE, env=env)
        eligible = demo_labels(get_authorized_accounts(env, token))
        if not eligible:
            print('Nessun conto Demo autorizzato. Controlla la selezione durante OAuth.')
            return 1
        print('Conti Demo autorizzati:')
        for i, (_, broker, ending) in enumerate(eligible, 1):
            print(f'{i}. {broker} - login finale ***{ending}')
        answer = input('Seleziona il numero del conto Demo (0 per annullare): ').strip()
        if not answer.isdecimal():
            print('Nessuna modifica effettuata.')
            return 1
        selection = int(answer)
        if selection == 0 or selection > len(eligible):
            print('Nessuna modifica effettuata.')
            return 1
        save_demo_selection(ENV_FILE, eligible[selection-1][0])
        print('DEMO CONFIGURATO. Il raccoglitore prezzi resta disattivato.')
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print('Configurazione non completata:', str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
