"""REMURA V30.0 LAB — one inventory GET + one exact-key SELECT at most.
No live invocation in module. Caller must independently verify account Free
and token permission, and persist inventory budget before calling.
"""
from urllib.parse import quote
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler
import cloudflare_d1_readonly_audit as cf
from d1_test_target_preflight_v1 import inspect_verified_inventory, TEST_DB, MAIN_DB
from v300_slot_custody import request_slots
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def build_transport(account_id,token,slots,cutoff,*,enabled=False):
    if enabled is not True:raise ValueError("disabled")
    account=quote(cf.require_account_id(account_id),safe="")
    token=cf.require_account_token(token)
    allowed=request_slots(slots,cutoff)
    used=False
    def fetch(query):
        nonlocal used
        if used or query!=allowed:raise ValueError("one_shot")
        used=True
        cf.urlopen=build_opener(ProxyHandler({}),NoRedirect()).open
        base="/accounts/"+account+"/d1/database"
        ids=inspect_verified_inventory(cf.api_request("GET",base+"?page=1&per_page=100",token))
        if ids[TEST_DB]==ids[MAIN_DB]:raise ValueError("isolation")
        return cf.api_request("POST",base+"/"+quote(ids[TEST_DB],safe="")+"/query",token,allowed)
    return fetch
