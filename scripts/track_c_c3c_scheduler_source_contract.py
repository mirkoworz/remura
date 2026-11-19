"""C3c-a: read-only ACTUAL repository scheduler-cadence contract, NO LIVE work.

Verify the *source code* that schedules core COT/cTrader and both retail
collectors. Enforce a static approved contract and fail closed on drift.
This does NOT inspect process runtime state, Oracle VM, GitHub Actions run
latency, provider publication dates, market trading sessions or whether
any collector is currently enabled. Those need later real evidence.

The 2026-11-09 synthetic lab frozen plan does NOT describe production:
COT is a 6h loop after work, cTrader rotates symbol batches at UTC M15
quarter+90s, private retail uses an opt-in 20m+90s loop, and GitHub
Myfxbook uses 7,27,47 cron UTC independently. None is a guaranteed
per-symbol/prospective data timestamp. DO NOT "upgrade" a synthetic slot
into real evidence by applying this contract.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re

MODE = "OFFLINE_STATIC_SOURCE_SCHEDULER_C3C_AUDIT_ONLY"
SCHEMA = "remura-track-c3c-static-cadence-source-v1"
DEFAULT_REPO = Path(__file__).resolve().parents[1]
EXPECTED = {
    "cot_stop_wait": "6 * 3600",
    "ctrader_stop_wait": "seconds_to_next_quarter()",
    "retail_stop_wait": "next_cycle(20 * 60, 90)",
    "ctrader_next_quarter": "((int(stamp) // quarter) + 1) * quarter + 90",
    "myfxbook_actions_cron": "7,27,47 * * * *",
}


def _node(expr):
    return ast.dump(ast.parse(expr, mode="eval").body,include_attributes=False)


def _must(actual, expected, label):
    if _node(actual) != _node(expected):
        raise ValueError("scheduler_source_drift_"+label)


def _function(tree,name):
    funcs=[x for x in tree.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))
           and x.name==name]
    if len(funcs)!=1:
        raise ValueError("missing_or_duplicate_core_scheduler_"+name)
    return funcs[0]


def _waits(fn):
    return [x.args[0] for x in ast.walk(fn)
            if isinstance(x,ast.Call)
            and isinstance(x.func,ast.Attribute)
            and isinstance(x.func.value,ast.Name)
            and x.func.value.id=="stop"
            and x.func.attr=="wait"
            and len(x.args)==1 and not x.keywords]


def _calls(fn,name):
    return [x for x in ast.walk(fn) if isinstance(x,ast.Call)
            and isinstance(x.func,ast.Name) and x.func.id==name]


def _require_wait(fn,expr,label):
    waits=_waits(fn)
    if len(waits)!=1 or ast.dump(waits[0],include_attributes=False)!=_node(expr):
        raise ValueError("scheduler_source_drift_"+label)


def _require_call(fn,name,label,expected_count=1):
    if len(_calls(fn,name))!=expected_count:
        raise ValueError("scheduler_source_drift_"+label)


def _get_expr(fn,name):
    found=[node.value for node in ast.walk(fn)
           if isinstance(node,(ast.Assign,ast.AnnAssign))
           and isinstance(node,ast.Assign)
           and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
           and node.targets[0].id==name]
    if len(found)!=1:
        raise ValueError("scheduler_source_drift_"+name)
    return found[0]


def _extract(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("scheduler_source_file_missing_or_symlink")
    return path.read_text(encoding="utf-8")


def _env_guard(fn,key,default,expected_count):
    # Extract exactly one literal env.get KEY/default from live main().
    matched=[]
    for call in ast.walk(fn):
        if (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
                and call.func.attr=="get" and len(call.args)==2
                and isinstance(call.func.value,ast.Attribute)
                and call.func.value.attr=="environ"
                and isinstance(call.func.value.value,ast.Name)
                and call.func.value.value.id=="os"):
            try: pair=tuple(ast.literal_eval(a) for a in call.args)
            except (ValueError,TypeError,LookupError): continue
            if pair[0]==key:
                matched.append(pair)
    if matched!=[(key,default)]*expected_count:
        raise ValueError("scheduler_enablement_contract_drift_"+key)


def inspect(*, root=None, mode=None):
    """Pure static read; ROOT may be a disposable test fixture.

    Reject new/unreviewed source changes rather than emitting a guessed
    schedule. This is an invariant test, not an execution or scheduler.
    """
    if mode!=MODE:
        raise ValueError("explicit_offline_scheduler_contract_mode_required")
    base=Path(root) if root is not None else DEFAULT_REPO
    if not base.is_dir() or base.is_symlink():
        raise ValueError("explicit_existing_repository_directory_required")
    server=base/"scripts/private_server.py"
    workflow=base/".github/workflows/myfxbook.yml"
    plan=base/"scripts/track_c_c3bc_frozen_plan.py"
    tree=ast.parse(_extract(server),filename=str(server))
    actual_workflow=_extract(workflow)
    lab=ast.parse(_extract(plan),filename=str(plan))

    cot=_function(tree,"cot_loop")
    price=_function(tree,"collector_loop")
    retail=_function(tree,"retail_loop")
    quarter=_function(tree,"seconds_to_next_quarter")
    main=_function(tree,"main")
    cot_enabled=_function(tree,"cot_sync_enabled")
    _require_wait(cot,EXPECTED["cot_stop_wait"],"cot_after_work_6hour")
    _require_call(cot,"collect_official_cot","cot_collector")
    _require_wait(price,EXPECTED["ctrader_stop_wait"],"ctrader_batch_quarter")
    _require_call(price,"collect_once","ctrader_batch_collector",expected_count=2)
    _require_wait(retail,EXPECTED["retail_stop_wait"],"vps_retail_20minutes")
    _require_call(retail,"retail_once","vps_retail_collector")
    quarter_secs=_get_expr(quarter,"quarter")
    if ast.literal_eval(quarter_secs)!=900:
        raise ValueError("scheduler_source_drift_ctrader_quarter_duration")
    if ast.dump(_get_expr(quarter,"next_event"),include_attributes=False)!=_node(
            EXPECTED["ctrader_next_quarter"]):
        raise ValueError("scheduler_source_drift_ctrader_quarter_90s_grace")

    _env_guard(main,"REMURA_COLLECTOR_ENABLED","0",expected_count=2)
    _env_guard(main,"REMURA_RETAIL_ENABLED","0",expected_count=1)
    # Private COT enabled by explicit opt-in or inherits explicitly opted-in
    # collector. A default-on research recorder would be a release blocker.
    calls=_calls(main,"cot_sync_enabled")
    if len(calls)!=1 or not _calls(main,"squalincome_enabled"):
        raise ValueError("scheduler_source_drift_private_cot_gate")
    if not any(isinstance(n,ast.Constant) and n.value=="REMURA_COT_SYNC_ENABLED"
               for n in ast.walk(cot_enabled)):
        raise ValueError("scheduler_source_drift_cot_gate_source")

    # GitHub Actions schedule syntax is UTC. Pull request workflow dispatch
    # is separate; no claim that GitHub fires at the exact scheduled minute.
    cron=re.findall(r"(?m)^\s*-\s*cron:\s*['\"]([^'\"]+)['\"]\s*$",
                    actual_workflow)
    if cron!=[EXPECTED["myfxbook_actions_cron"]]:
        raise ValueError("scheduler_source_drift_myfxbook_actions_cron")
    if "workflow_dispatch:" not in actual_workflow:
        raise ValueError("scheduler_source_drift_myfxbook_manual_dispatch")
    if "python scripts/update_myfxbook.py" not in actual_workflow:
        raise ValueError("scheduler_source_drift_myfxbook_job")

    # Never allow the lab-only Monday/weekly/30m plan to be silently
    # represented as the source owner's schedule. This is a deliberate
    # mismatch and a NO-GO until a new prospectively approved protocol.
    source_spec=_function(lab,"_frozen")
    if not source_spec:
        raise ValueError("synthetic_source_policy_absent")
    source_assignments=[n for n in lab.body if isinstance(n,ast.Assign)
                        and len(n.targets)==1
                        and isinstance(n.targets[0],ast.Name)
                        and n.targets[0].id=="SOURCES"]
    if len(source_assignments)!=1:
        raise ValueError("unreviewed_lab_source_policy")
    lab_sources=ast.literal_eval(source_assignments[0].value)
    if (len(lab_sources)!=3
            or {(a,b,c) for a,b,c in lab_sources}!={
                ("cot","weekly-monday-12utc-poll-not-publication",604800),
                ("ctrader","15m-synthetic-poll",900),
                ("retail","30m-synthetic-poll",1800)}):
        raise ValueError("unreviewed_lab_policy_changed")
    semantics={
        "cotCoreSecondsAfterCompletion":21600,
        "ctraderBatchQuarterSeconds":900,
        "ctraderAfterQuarterGraceSeconds":90,
        "privateRetailCycleSeconds":1200,
        "privateRetailAfterCycleGraceSeconds":90,
        "myfxbookActionsCronUtc":cron[0],
        "sourcePaths":[str(server.relative_to(base)),
                       str(workflow.relative_to(base))],
    }
    digest=hashlib.sha256(json.dumps(semantics,sort_keys=True,
                separators=(",",":"),ensure_ascii=True).encode("ascii")).hexdigest()
    return {
        "schema":SCHEMA,
        "status":"OFFLINE_SOURCE_REPOSITORY_CADENCE_AUDITED",
        "approvedSourceSemanticsSha256":digest,
        "cadences":semantics,
        "liveCadenceEqualsFrozenLabPlan":False,
        "liveScanTimesReconstructibleExactly":False,
        "perSymbolM15EveryQuarterProven":False,
        "githubCronRunsOnTimeProven":False,
        "providerDataFreshnessGuaranteed":False,
        "cotReportPublishedAtPoll":False,
        "retailProviderUpdatedAtPoll":False,
        "liveEnabled":False,
        "collectorDefaultsStillOff":True,
        "actualRuntimeConfigurationVerified":False,
        "externalCostsVerified":False,
        "newProviderCalls":0,
    }
