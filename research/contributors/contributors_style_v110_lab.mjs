// Shared v1.10 theme based on the v1.08 cockpit palette and navigation.
export const CONTRIBUTORS_CSS_V110 = `
:root{color-scheme:dark;--bg:#07121a;--panel:#102833;--line:#2d4f58;--aqua:#69edca;--ink:#edf9f5;--muted:#a0bac0;--blue:#91baff;--gold:#f4c890;--red:#f5909c;--radius:19px;--control:12px;--focus:var(--aqua)}
*{box-sizing:border-box}html{scroll-padding-top:16px}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a,summary,button,input,select{font:inherit}a{color:var(--aqua);text-decoration:none}a:focus-visible,summary:focus-visible,button:focus-visible,.scroll:focus-visible{outline:2px solid var(--focus);outline-offset:3px}
.version{padding:calc(8px + env(safe-area-inset-top,0px)) 12px 8px;background:#102c35;border-bottom:1px solid #39655d;color:#b9f8df;text-align:center;font-size:11px;font-weight:700;overflow-wrap:anywhere}
.shell{max-width:1230px;margin:auto;padding:20px max(16px,env(safe-area-inset-right,0px)) calc(40px + env(safe-area-inset-bottom,0px)) max(16px,env(safe-area-inset-left,0px))}
.masthead{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:12px;margin-bottom:16px}.brand{font-size:23px;font-weight:890;letter-spacing:.15em;color:var(--aqua)}.brand small{display:block;color:var(--muted);font-size:10px;letter-spacing:.06em;font-weight:700}
.tag,.eyebrow{font-size:11px;font-weight:850;letter-spacing:.09em;color:var(--aqua)}.tag{border:1px solid #4c8579;border-radius:999px;padding:5px 9px;display:inline-block}
.navigation{display:grid;gap:10px;margin:0 0 20px}.primary-nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.nav-link,.action{min-height:46px;display:flex;align-items:center;justify-content:center;border:1px solid #355762;border-radius:var(--control);padding:10px 12px;background:#18323e;color:var(--ink);font-weight:750;font-size:14px;text-align:center}.nav-link.active,.action{background:var(--aqua);color:#0a2929;border-color:var(--aqua)}.menu{border:1px solid var(--line);background:#0d2731;border-radius:var(--control)}.menu-body{padding:8px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.menu-body .nav-link{justify-content:flex-start;text-align:left}
summary{list-style:none;cursor:pointer;min-height:46px;display:flex;justify-content:space-between;align-items:center;gap:10px;color:var(--aqua);font-weight:850;padding:10px 14px}summary::-webkit-details-marker{display:none}.chevron{flex:none;width:9px;height:9px;border-right:2px solid currentColor;border-bottom:2px solid currentColor;transform:rotate(45deg);margin:0 5px 4px}details[open]>summary .chevron{transform:rotate(225deg)}
.hero{padding:clamp(20px,4vw,45px);background:radial-gradient(ellipse at 95% 0%,#18635785,transparent 70%),linear-gradient(130deg,#13323d,#0b202c 68%);border:1px solid #2c585d;border-radius:24px;min-width:0}.hero h1{font-size:clamp(30px,5vw,54px);line-height:1.08;letter-spacing:-.04em;margin:8px 0 14px;overflow-wrap:anywhere}.hero p{margin:0;color:#c1d9d8}
h2{font-size:clamp(19px,3vw,25px);line-height:1.25;letter-spacing:-.02em;margin:0 0 12px}p{color:var(--muted);margin:8px 0 12px;overflow-wrap:anywhere}.panel{min-width:0;margin:16px 0;border:1px solid var(--line);border-radius:var(--radius);padding:20px;background:linear-gradient(155deg,#102b36,#0c1e29)}.market-group{padding:4px 12px 8px}.market-group[open]{padding-bottom:14px}.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:16px 0}.metric{min-width:0;border:1px solid var(--line);border-radius:12px;background:#102c35;padding:12px 8px}.metric small{display:block;color:var(--muted);font-size:11px;overflow-wrap:anywhere}.metric strong{display:block;color:var(--aqua);font-size:27px;font-variant-numeric:tabular-nums}.hint{font-size:13px}.notice{border:1px solid #64543e;background:#2c2a21;color:var(--gold);padding:12px;border-radius:var(--control)}
.scroll{overflow-x:auto;max-width:100%;overscroll-behavior-inline:contain;border:1px solid #355a61;border-radius:10px}table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:11px 10px;border-bottom:1px solid #284a55;text-align:right}th:first-child{text-align:left}thead th{color:var(--aqua);background:#143743}tbody th{position:sticky;left:0;background:#102833;z-index:1}tbody tr:last-child>*{border-bottom:0}.action{width:fit-content}footer{font-size:12px;color:var(--muted);margin-top:24px;padding-top:16px;border-top:1px solid var(--line)}
@media(max-width:540px){.shell{padding-top:14px}.panel{padding:15px}.market-group{padding:3px 8px 8px}.menu-body{grid-template-columns:1fr}.hero{padding:20px}.metric strong{font-size:24px}.metric small{font-size:10px}.action{width:100%}}
@media(max-width:340px){.primary-nav{grid-template-columns:1fr}.metrics{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important}}
`;

export const CONTRIBUTORS_FORMS_CSS_V110 = `
[hidden] { display: none !important; }
.brand { display: inline-flex; min-height: 46px; flex-direction: column; justify-content: center; }
.panel { background: var(--panel); }
.work-grid, .access-forms { display: grid; gap: 16px; margin: 16px 0; }
.work-grid { grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); align-items: start; }
.work-grid > .panel { margin: 0; }
.access-forms { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.access-forms .panel { margin: 0; }
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.field { min-width: 0; }
.field.wide { grid-column: 1 / -1; }
label { display: block; font-weight: 700; margin: 0 0 4px; }
input, select, textarea, button { font: inherit; }
input, select, textarea {
  min-height: 46px;
  width: 100%;
  color: var(--ink);
  background: #0b202c;
  padding: 9px 11px;
  border: 1px solid #4a6c75;
  border-radius: var(--control);
  font-size: 16px;
}
textarea { min-height: 85px; resize: vertical; }
input::placeholder, textarea::placeholder { color: var(--muted); }
input:focus-visible, select:focus-visible, textarea:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 3px;
}
button {
  min-height: 46px;
  border: 1px solid var(--aqua);
  border-radius: var(--control);
  padding: 9px 14px;
  background: var(--aqua);
  color: #0a2929;
  font-size: 14px;
  font-weight: 750;
  cursor: pointer;
}
button.secondary { border-color: #4a6c75; color: var(--ink); background: #18323e; }
button.danger { border-color: var(--red); color: var(--red); background: transparent; }
button:disabled { opacity: .58; cursor: not-allowed; }
button:focus-visible { outline: 2px solid var(--focus); outline-offset: 3px; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 0; }
.status { color: var(--muted); overflow-wrap: anywhere; }
.status:empty { margin: 0; }
.status[data-tone="success"] { color: var(--aqua); }
.status[data-tone="warning"] { color: var(--gold); }
.status[data-tone="error"] { color: var(--red); }
.receipt { padding: 3px 0; margin: 8px 0; border: 1px solid var(--line); border-radius: var(--control); }
.receipt summary { flex-wrap: wrap; justify-content: flex-start; gap: 5px 12px; }
.receipt .chevron { margin-left: auto; }
.receipt-actions { padding: 0 14px 12px; }
.receipt dl { display: grid; grid-template-columns: fit-content(40%) 1fr; gap: 4px 12px; padding: 0 14px; }
.receipt dt, .receipt dd { min-width: 0; margin: 0; overflow-wrap: anywhere; }
.receipt dt { color: var(--muted); }
.state { color: var(--blue); }
.state[data-state="UNREVIEWED"], .state[data-state="INVITED"] { color: var(--gold); }
.state[data-state="APPROVED"], .state[data-state="ACTIVE"] { color: var(--aqua); }
.state[data-state="REJECTED"], .state[data-state="REVOKED"] { color: var(--red); }
.work-table { white-space: normal; }
.work-table th, .work-table td { text-align: left; vertical-align: middle; }
.work-table tbody th { position: static; }
.work-table td > button { white-space: nowrap; }
.work-table td { overflow-wrap: anywhere; }

@media (max-width: 840px) {
  .work-grid, .access-forms { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 540px) {
  .fields { grid-template-columns: minmax(0, 1fr); }
  .actions button { flex: 1 1 auto; }
}
`;
