#!/usr/bin/env python3
# REMURA Contributors v0.94 LAB — deterministic 1–2 person pilot scope contract.
"""Offline prospective onboarding plan, NOT an authorization middleware.

The existing v0.92 Worker/D1/Access boundaries remain authoritative *if*
deployed with separate permission and identity verification. This contract
never validates Access JWT, Cloudflare seats/billing, Safari sessions, actual
permissions, or real users. Fixture IDs only; no emails, tokens, or secrets.
"""
from __future__ import annotations
from hashlib import sha256
import json
import re

SCHEMA = "remura.contributors.pilot_scope_contract.v094.lab"
FIXTURE = re.compile(r"^fixture-(?:owner|contrib-[a-z0-9]{2,12})$")
VISIBLE = frozenset(("REMURA_READ_ALLOWED_SECTIONS","READ_OWN_LEVELS"))
MUTATE = frozenset(("SUBMIT_OWN_LEVEL","AMEND_OWN_LEVEL"))
OWNER = frozenset(("REMURA_READ_ALLOWED_SECTIONS","OWNER_QUEUE","OWNER_REVIEW",
                   "OWNER_APPROVE_OTHERS","OWNER_AUDIT_READ"))
CGRANTS = VISIBLE | MUTATE
DANGEROUS = frozenset((
    "WRITE_COT","WRITE_ORACLE","READ_SECRETS","DEPLOY_PRODUCTION",
    "ALTER_ACCESS_POLICY","EDIT_OTHERS_LEVELS","APPROVE_SELF",
    "OWNER_QUEUE","OWNER_REVIEW","OWNER_APPROVE_OTHERS","OWNER_AUDIT_READ"
))
ALL_ACTIONS = OWNER | CGRANTS | DANGEROUS
SENSITIVE_OWNER_ACTIONS = frozenset(("OWNER_REVIEW","OWNER_APPROVE_OTHERS","OWNER_AUDIT_READ",
                                      "OWNER_QUEUE"))
SUBJECT_ACTIONS = frozenset(("READ_OWN_LEVELS","SUBMIT_OWN_LEVEL","AMEND_OWN_LEVEL"))
MAX_ACTORS = 3

class PilotScopeError(ValueError):
    pass

def _ident(value):
    if type(value) is not str or FIXTURE.fullmatch(value) is None:
        raise PilotScopeError("fixture_identifier_only")
    return value

def compile_pilot(*, owner_subject, contributor_subjects):
    """Compiles a non-deployable human-reviewed scope inventory."""
    _ident(owner_subject)
    if owner_subject != "fixture-owner":
        raise PilotScopeError("separate_owner_required")
    if (type(contributor_subjects) not in (list,tuple)
            or len(contributor_subjects) not in (1,2)):
        raise PilotScopeError("one_or_two_fixture_contributors_required")
    ids = [_ident(x) for x in contributor_subjects]
    if any(not x.startswith("fixture-contrib-") for x in ids):
        raise PilotScopeError("owner_cannot_be_invited_as_contributor")
    if len(set(ids)) != len(ids) or owner_subject in ids:
        raise PilotScopeError("duplicate_identity_not_allowed")
    policy = {"fixture-owner": sorted(OWNER)}
    for identifier in sorted(ids):
        policy[identifier] = sorted(CGRANTS)
    # Deliberate absence of real email, UUID, Access token, service identity.
    packed = json.dumps(policy,sort_keys=True,separators=(",",":")).encode()
    return {
        "schema":SCHEMA,
        "roster":policy,
        "scope_sha256":sha256(packed).hexdigest(),
        "owner_approval_separate_from_contributor_mutation":True,
        "contributors":len(ids),
        "network_calls":0,
        "cloudflare_access_seats_verified":False,
        "cloudflare_d1_quota_verified":False,
        "github_actions_quota_verified":False,
        "safari_login_revocation_tested":False,
        "policy_installed_on_worker":False,
        "live_identity_verified":False,
        "real_pilot_allowed":False,
        "status":"OFFLINE_SCOPE_PLAN_NOT_AUTHORIZATION",
    }

def model_action(plan, *, claimed_actor, action, target_subject=None,
                 approval_author_subject=None):
    """Intended least-privilege behavior ONLY; caller IDs cannot authorize HTTP."""
    if (type(plan) is not dict or plan.get("schema") != SCHEMA
            or plan.get("status") != "OFFLINE_SCOPE_PLAN_NOT_AUTHORIZATION"
            or type(plan.get("roster")) is not dict):
        raise PilotScopeError("untrusted_scope_plan")
    if type(action) is not str or action not in ALL_ACTIONS:
        return {"planned_allow":False,"reason":"UNLISTED_ACTION_FAIL_CLOSED",
                "runtime_authorization":False}
    # Never infer role from headers, cookies, body or user-controlled profile.
    # This function operates on an explicitly synthetic preview roster.
    roster=plan["roster"]
    try:
        expected=compile_pilot(
            owner_subject="fixture-owner",
            contributor_subjects=sorted(x for x in roster if x != "fixture-owner"))
    except (PilotScopeError, TypeError, ValueError):
        expected=None
    if (expected is None or plan.get("scope_sha256")!=expected["scope_sha256"]
            or roster!=expected["roster"]):
        return {"planned_allow":False,"reason":"SCOPE_MANIFEST_CHANGED",
                "runtime_authorization":False}
    if (type(claimed_actor) is not str or claimed_actor not in roster or
            type(roster[claimed_actor]) is not list
            or set(roster[claimed_actor]) !=
              (OWNER if claimed_actor == "fixture-owner" else CGRANTS)):
        return {"planned_allow":False,"reason":"ACTOR_OR_PLAN_NOT_TRUSTED",
                "runtime_authorization":False}
    intended = action in roster[claimed_actor]
    if action in SUBJECT_ACTIONS:
        intended = intended and target_subject == claimed_actor
    if action == "OWNER_APPROVE_OTHERS":
        intended = (intended and type(target_subject) is str and
                    target_subject in roster and target_subject != claimed_actor
                    and target_subject.startswith("fixture-contrib-")
                    and approval_author_subject != claimed_actor)
    if action in DANGEROUS - SENSITIVE_OWNER_ACTIONS:
        intended = False
    return {
        "planned_allow":bool(intended),
        "reason":"SYNTHETIC_SCOPE_PREVIEW_ONLY" if intended else "OUT_OF_SCOPE",
        "runtime_authorization":False,
        "access_jwt_independently_verified":False,
        "d1_ownership_verified":False,
        "production_write_enabled":False,
    }

def review_claimed_ui(plan, *, actor, requested_actions):
    """UI affordances may hide controls, but never grant server permissions."""
    if type(requested_actions) not in (list,tuple) or len(requested_actions)>32:
        raise PilotScopeError("bounded_ui_claims_required")
    if any(type(x) is not str for x in requested_actions):
        raise PilotScopeError("invalid_ui_action")
    if len(set(requested_actions))!=len(requested_actions):
        raise PilotScopeError("duplicate_ui_action_claim")
    claims = set(requested_actions)
    allowed = {action for action in claims
               if model_action(plan,claimed_actor=actor,action=action,
                               target_subject=actor)["planned_allow"]}
    extras = sorted(claims-allowed)
    return {
        "status":"UI_SCOPE_MATCH_CLAIM_ONLY" if not extras else
                 "UI_SCOPE_EXCEEDS_INTENDED_POLICY",
        "unapproved_ui_actions":extras,
        "capability_list_is_not_an_access_token":True,
        "backend_authorization_required":True,
        "pilot_go":False,
    }
