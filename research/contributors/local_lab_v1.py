# REMURA Contributors v0.5 LAB — 14/11/2026 23:35 CET
"""Local synthetic browser harness. NOT authentication or deployable service.
Only loopback, temporary SQLite, fixed fictional identities and mappings.
A local operator can deliberately switch between all demo roles.
"""
import argparse
from datetime import datetime,timezone
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import secrets
import tempfile
from urllib.parse import parse_qsl
from uuid import uuid4
from archive_v1 import Archive,CatalogEntry,FIELDS
from ledger_v1 import Principal
from owner_preview_v1 import LABELS

CATALOG=(
    CatalogEntry("EURUSD","OANDA","EURUSD","SPOT","","synthetic-fx"),
    CatalogEntry("EURUSD","FXCM","EURUSD","SPOT","","synthetic-fx"),
    CatalogEntry("NAS100","PEPPERSTONE","NAS100","CFD","","synthetic-index"),
    CatalogEntry("NAS100","CAPITALCOM","US100","CFD","","synthetic-index"),
    CatalogEntry("XAUUSD","OANDA","XAUUSD","CFD","","synthetic-metal"),
)
ROLES={"/friend-a":Principal("friend-a","CONTRIBUTOR"),
       "/friend-b":Principal("friend-b","CONTRIBUTOR"),
       "/owner":Principal("owner","OWNER")}
MAX_BODY=8192
CSP="default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
STYLE=":root{color-scheme:dark;--bg:#07121a;--panel:#101f2a;--ink:#e8f4f3;--muted:#8ba7ae;--aqua:#69edca}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 system-ui}main{max-width:600px;margin:auto;padding:18px}.release{background:#102c35;color:#b9f8df;font-size:11px;text-align:center;padding:6px}nav{display:flex;flex-wrap:wrap;gap:12px}a{color:var(--aqua)}section,article,form{border:1px solid #203642;border-radius:19px;background:linear-gradient(#10222e,#101e29);padding:16px;margin:14px 0;overflow-wrap:anywhere}label{display:block;margin:12px 0 5px}input,select,button{width:100%;font:inherit;padding:12px;min-height:44px;border:1px solid #37606a;border-radius:12px;background:#102b35;color:var(--ink)}button{margin-top:12px;background:var(--aqua);color:#052c28;font-weight:800}small{color:var(--muted)}h1,h2{letter-spacing:-.035em}strong{color:var(--aqua)}"
def e(x):return escape(str(x),quote=True)
def stamp():return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def options(values):
    return "".join('<option value="'+e(v)+'">'+e(label)+'</option>' for v,label in values)
def hidden(name,value):
    return '<input type="hidden" name="'+e(name)+'" value="'+e(value)+'">'
def field(name,label,value="",extra=""):
    return '<label>'+e(label)+'<input name="'+e(name)+'" value="'+e(value)+'" '+extra+'></label>'
def select(name,label,values):
    return '<label>'+e(label)+'<select name="'+e(name)+'">'+options(values)+'</select></label>'

class Lab:
    def __init__(self,archive,*,clock=stamp):
        self.archive=archive
        self.clock=clock
        self.csrf=secrets.token_urlsafe(32)

    def page(self,path,message=""):
        principal=ROLES[path]
        parts=['<!doctype html><html lang="it"><head><meta charset="utf-8">',
               '<meta name="viewport" content="width=device-width,initial-scale=1">',
               '<title>REMURA Contributors v0.5 LAB</title><style>'+STYLE+'</style></head><body>',
               '<div class="release">REMURA · Contributors v0.5 LAB · 14/11/2026 23:35 CET</div><main>',
               '<small>REMURA / VOLUMETRICA / CONTRIBUTORS</small><h1>Collaudo locale</h1>',
               '<p><strong>SOLO DATI FITTIZI</strong> · Ruoli dimostrativi selezionabili. Non è Google login o un controllo di accesso reale. Non inserire dati personali.</p>',
               '<nav><a href="/friend-a">Amico A</a><a href="/friend-b">Amico B</a><a href="/owner">Proprietario</a></nav>',
               '<p>Ruolo demo: '+e(principal.subject)+'</p><p role="status">'+e(message)+'</p>']
        if principal.role=="CONTRIBUTOR":
            parts.extend(['<form method="post" action="'+e(path)+'"><h2>Nuovo livello</h2>',
                hidden("csrf",self.csrf),hidden("request_id",str(uuid4())),
                select("market","1. Pair / strumento",[(x,x) for x in ("EURUSD","NAS100","XAUUSD")]),
                select("provider","2. Broker / fonte",[(x,y) for x,y in (("OANDA","OANDA"),("FXCM","FXCM"),("PEPPERSTONE","Pepperstone"),("CAPITALCOM","Capital.com"))]),
                field("ticker","Ticker esatto","EURUSD",'required maxlength="24"'),
                select("product","Tipo prodotto",[("SPOT","Spot"),("CFD","CFD")]),
                hidden("contract",""),
                select("period","Periodo",[(x,x) for x in ("DAY","WEEK","CURRENT_MONTH","PREVIOUS_MONTH")]),
                select("kind","Tipologia",[("DELTA_PEAK","Picco di delta"),("EFFORT_RESULT","Effort Result"),("OTHER_VOLUME_LEVEL","Altro")]),
                field("price","Prezzo fittizio","1.08540",'required inputmode="decimal" maxlength="17"'),
                field("anchor_utc","Inizio periodo dichiarato UTC",self.clock(),'required maxlength="20"'),
                field("observed_utc","Istante osservato UTC",self.clock(),'required maxlength="20"'),
                field("note","Nota facoltativa","",'maxlength="280"'),
                '<p><small>Solo cinque mapping sintetici sono ammessi in questo collaudo; catalogo completo da verificare prima del reale. Nessuna conversione tra fonti.</small></p>',
                '<button>Registra livello demo</button></form><h2>Le tue ricevute</h2>'])
            rows=self.archive.receipts(principal)
        else:
            parts.append("<h2>Revisione contributi</h2>")
            rows=self.archive.queue(principal)
        for row in rows:
            p=row["data"]
            parts.extend(['<article><small>#'+e(row["id"])+' · '+e(row.get("subject","Tuo contributo"))+'</small>',
                '<h2>'+e(p["market"])+' · '+e(p["price"])+'</h2>',
                '<p>'+e(p["provider"])+':'+e(p["ticker"])+' · '+e(p["product"])+' · '+e(p["period"])+' · '+e(p["kind"])+'</p>',
                '<p>Anchor: '+e(p["anchor_utc"])+'<br>Osservato: '+e(p["observed_utc"])+'<br>Ricevuto: '+e(row["received_utc"])+'</p>',
                '<p>Nota: '+e(p["note"])+'</p><strong>'+e(LABELS[row["status"]])+'</strong>'])
            if principal.role=="OWNER":
                for h in row["history"]:
                    parts.append('<p>'+e(h["at_utc"])+' · '+e(LABELS[h["action"]])+' · '+e(h["reason"])+'</p>')
                actions={"UNREVIEWED":("APPROVED","REJECTED"),"APPROVED":("REVOKED",)}.get(row["status"],())
                for action in actions:
                    parts.extend(['<form method="post" action="/owner">',hidden("csrf",self.csrf),
                                  hidden("entry_id",row["id"]),hidden("action",action),
                                  field("reason","Motivazione","",'required maxlength="280"'),
                                  '<button>'+e({"APPROVED":"Approva","REJECTED":"Rifiuta","REVOKED":"Revoca approvazione"}[action])+'</button></form>'])
            parts.append("</article>")
        if not rows:parts.append("<p>Nessun contributo demo.</p>")
        return "".join(parts)+"</main></body></html>"

    def submit(self,path,body):
        principal=ROLES[path]
        if type(body) is not bytes or len(body)>MAX_BODY:raise ValueError("body")
        pairs=parse_qsl(body.decode("utf-8",errors="strict"),keep_blank_values=True,strict_parsing=True,
                        max_num_fields=16,encoding="utf-8",errors="strict")
        p=dict(pairs)
        if len(pairs)!=len(p):raise ValueError("duplicate_field")
        token=p.pop("csrf","")
        if not token.isascii() or not secrets.compare_digest(token,self.csrf):raise PermissionError("csrf")
        if principal.role=="CONTRIBUTOR":
            if set(p)!=FIELDS:raise ValueError("fields")
            p["price"]=p["price"].strip().replace(",",".")
            return self.archive.submit(principal,p,received_utc=self.clock())
        if set(p)!={"entry_id","action","reason"}:raise ValueError("fields")
        if not p["entry_id"].isascii() or not p["entry_id"].isdigit() or len(p["entry_id"])>9:
            raise ValueError("entry_id")
        return self.archive.review(principal,int(p["entry_id"]),p["action"],at_utc=self.clock(),reason=p["reason"])

def handler(lab):
    class Handler(BaseHTTPRequestHandler):
        # Local-only harness, no URL or body logging; no live deployment.
        def log_message(self,*args):pass
        def setup(self):
            super().setup()
            self.connection.settimeout(5)
        def respond(self,status,body,location=None):
            data=body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Security-Policy",CSP)
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("X-Frame-Options","DENY")
            self.send_header("Referrer-Policy","no-referrer")
            if location:self.send_header("Location",location)
            self.send_header("Content-Length",str(len(data)))
            self.end_headers();self.wfile.write(data)
        def origin(self):
            return "http://127.0.0.1:"+str(self.server.server_port)
        def allowed(self):
            return self.headers.get_all("Host")==[self.origin().split("://")[1]]
        def do_GET(self):
            if not self.allowed():return self.respond(403,"Forbidden")
            if self.path=="/":return self.respond(303,"",location="/friend-a")
            if self.path not in ROLES:return self.respond(404,"Not found")
            return self.respond(200,lab.page(self.path))
        def do_POST(self):
            if not self.allowed() or self.headers.get_all("Origin")!=[self.origin()]:
                return self.respond(403,"Forbidden")
            if self.path not in ROLES:return self.respond(404,"Not found")
            if self.headers.get_all("Transfer-Encoding") or self.headers.get_all("Content-Type")!=["application/x-www-form-urlencoded"]:
                return self.respond(415,"Unsupported")
            lengths=self.headers.get_all("Content-Length") or []
            if len(lengths)!=1 or not lengths[0].isascii() or not lengths[0].isdigit() or len(lengths[0])>5:
                return self.respond(400,"Bad request")
            n=int(lengths[0])
            if not 0<n<=MAX_BODY:return self.respond(413,"Too large")
            try:
                body=self.rfile.read(n)
                if len(body)!=n:raise ValueError("incomplete_body")
                lab.submit(self.path,body)
            except PermissionError:return self.respond(403,"Forbidden")
            except (ValueError,UnicodeError):return self.respond(400,lab.page(self.path,"Contributo non valido o già presente. Controlla campi, mapping e tempi."))
            return self.respond(303,"",location=self.path)
    return Handler

def main():
    p=argparse.ArgumentParser(description="REMURA local synthetic LAB only")
    p.add_argument("--synthetic-lab",action="store_true",required=True)
    p.parse_args()
    with tempfile.TemporaryDirectory(prefix="remura-contributors-lab-") as root:
        archive=Archive(Path(root).resolve(),catalog=CATALOG,contributors=["friend-a","friend-b"],owners=["owner"],synthetic=True)
        try:
            with HTTPServer(("127.0.0.1",0),handler(Lab(archive))) as server:
                print("SOLO DEMO LOCALE: http://127.0.0.1:"+str(server.server_port),flush=True)
                print("Ruoli fittizi, dati cancellati alla chiusura normale. NON esporre tramite tunnel.",flush=True)
                try:server.serve_forever()
                except KeyboardInterrupt:pass
        finally:archive.close()
if __name__=="__main__":main()
