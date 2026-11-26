"""Unmounted LAB route. Access context MUST be supplied by verified server middleware.
No header, URL, client role or cookie can substitute for authentication.
"""
from v308_render import render
def response(path,method,identity,summary):
    headers={"Cache-Control":"no-store, private","Content-Type":"text/html; charset=utf-8","X-Content-Type-Options":"nosniff","Content-Security-Policy":"default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"}
    if path!="/owner/intelligence/":return 404,headers,"Not found"
    if method!="GET":return 405,headers,"Method not allowed"
    if not isinstance(identity,dict) or identity.get("verified") is not True or identity.get("role")!="OWNER" or identity.get("slot")!="owner":return 403,headers,"Forbidden"
    try:return 200,headers,render(summary,authenticated_owner=True)
    except (ValueError,TypeError,KeyError):return 503,headers,"Summary unavailable"
