import { COT_ARCHIVE_V110 } from './cot_archive_v110_lab.mjs';
import { CONTRIBUTORS_CSS_V110 as theme, CONTRIBUTORS_FORMS_CSS_V110 } from './contributors_style_v110_lab.mjs';
export { CONTRIBUTORS_BROWSER_V110 } from './contributors_browser_v110_lab.mjs';

export const CONTRIBUTORS_CSS_V110 = theme + CONTRIBUTORS_FORMS_CSS_V110;
const VERSION = 'REMURA Contributors V30.18 LAB';
const UPDATED = '27/11/2026 09:52 CET (Europe/Rome)';
const SLOTS = ['friend-a', 'friend-b', 'friend-c'];
const NAV_SECTIONS = [
  ['cot', 'Shark Cockpit · COT'],
  ['valute', 'Fattori valutari'],
  ['forex', 'Forex · 28 cross'],
  ['futures-finanziari', 'Futures finanziari'],
  ['futures-fisici', 'Metalli ed energia'],
  ['moduli', 'Disponibilità moduli'],
];
const CHEVRON = '<span class="chevron" aria-hidden="true"></span>';

function shell({ role, home, slot, caption, navigation, body, script, write }) {
  return `<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#07121a">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <title>${caption} · ${VERSION}</title>
  <link rel="stylesheet" href="${home}contributors-v110.css">
  ${script ? `<script type="module" src="${home}contributors-v110.js"></script>` : ''}
</head>
<body data-slot="${slot}" data-write="${write}">
  <div class="version">${VERSION} · <time datetime="2026-11-27T09:52:00+01:00">${UPDATED}</time></div>
  <main class="shell">
    <header class="masthead">
      ${role === 'INVITED'
        ? '<span class="brand">REMURA<small>Segui le tracce istituzionali</small></span>'
        : `<a class="brand" href="${home}" aria-label="REMURA, torna alla dashboard">REMURA<small>Segui le tracce istituzionali</small></a>`}
      <span class="tag">${role === 'INVITED' ? 'INVITO CONTRIBUTORS' : role}</span>
    </header>
    ${navigation}
    ${body}
    <footer>${VERSION}</footer>
  </main>
</body>
</html>`;
}

function navLink(path, name, active = false) {
  return `<a class="nav-link${active ? ' active' : ''}" href="${path}"${active ? ' aria-current="page"' : ''}>${name}</a>`;
}

function navigation(home, label, levels) {
  return `<nav aria-label="Menu REMURA" class="navigation">
    <div class="primary-nav">${navLink(home, 'Dashboard', !levels)}${navLink(`${home}levels/`, label, levels)}</div>
    <details class="menu">
      <summary>Esplora REMURA${CHEVRON}</summary>
      <div class="menu-body">${NAV_SECTIONS.map(([id, name]) => navLink(`${home}#${id}`, name)).join('')}</div>
    </details>
  </nav>`;
}

function hero(title, description) {
  return `<section class="hero"><h1>${title}</h1><p>${description}</p></section>`;
}

function status(id, text = '') {
  return `<p class="status" id="${id}" role="status" aria-live="polite">${text}</p>`;
}

function field(id, label, input, wide = false) {
  return `<div class="field${wide ? ' wide' : ''}"><label for="${id}">${label}</label>${input}</div>`;
}

function controls(id, label, data, { wide = false, placeholder = '' } = {}) {
  const options = data.map(([value, text]) => `<option value="${value}">${text}</option>`).join('');
  return field(id, label, `<select id="${id}" required>${placeholder ? `<option value="">${placeholder}</option>` : ''}${options}</select>`, wide);
}

function button(id, label, { type = 'button', modifier = 'secondary', hidden = false, disabled = false } = {}) {
  return `<button id="${id}" type="${type}" class="${modifier}"${hidden ? ' hidden' : ''}${disabled ? ' disabled' : ''}>${label}</button>`;
}

function dataPanel({ title, name, prefix, heading, hidden = false }) {
  return `<section class="panel" id="${name}"${hidden ? ' hidden' : ''} aria-labelledby="${name}Heading">
    <h2 id="${name}Heading">${title}</h2>
    ${status(`${prefix}Status`, heading)}
    <div id="${prefix}Rows"></div>
    <div class="actions">
      ${button(`${prefix}Load`, 'Aggiorna')}
      ${button(`${prefix}Next`, 'Pagina successiva', { hidden: true })}
    </div>
  </section>`;
}

const PERIODS = [['DAY', 'Giorno'], ['WEEK', 'Settimana'], ['CURRENT_MONTH', 'Mese corrente'], ['PREVIOUS_MONTH', 'Mese precedente']];
const KINDS = [['DELTA_PEAK', 'Picco delta'], ['EFFORT_RESULT', 'Effort / result'], ['OTHER_VOLUME_LEVEL', 'Altro livello volumetrico']];

function contributorLevels(write, read) {
  const unavailable = write ? 'Caricamento catalogo…' : 'Invio dei livelli disattivato.';
  return `${hero('I miei livelli', 'Proponi livelli volumetrici e segui le decisioni nelle tue ricevute.')}
  <section class="panel" id="pendingAttempt" hidden aria-labelledby="pendingHeading">
    <h2 id="pendingHeading">Verifica dell’invio</h2>
    <p id="pendingMessage" class="notice"></p>
    <div class="actions">
      ${button('checkAttempt', 'Verifica la ricevuta')}
      ${button('retryAttempt', 'Reinvia lo stesso livello', { hidden: true, modifier: '' })}
      ${button('clearAttempt', 'Chiudi il tentativo', { hidden: true })}
    </div>
  </section>
  ${status('intakeStatus')}
  <div class="work-grid">
    <section class="panel" aria-labelledby="intakeHeading">
      <h2 id="intakeHeading">Nuova proposta</h2>
      ${status('catalogStatus', unavailable)}
      ${button('catalogLoad', 'Ricarica catalogo', { hidden: true })}
      <form id="intake" autocomplete="off" hidden>
        <div class="fields">
          ${controls('market', 'Strumento', [], { placeholder: 'Seleziona strumento' })}
          ${controls('provider', 'Fonte', [], { placeholder: 'Seleziona fonte' })}
          ${controls('mapping', 'Serie / contratto', [], { wide: true, placeholder: 'Seleziona serie' })}
          ${controls('period', 'Periodo', PERIODS)}
          ${controls('kind', 'Metodologia', KINDS)}
          ${field('price', 'Prezzo originale del grafico', '<input id="price" inputmode="decimal" maxlength="17" required>')}
          ${field('anchor', 'Riferimento (ora Roma)', '<input id="anchor" type="datetime-local" step="1" required>')}
          ${field('observed', 'Osservato (ora Roma)', '<input id="observed" type="datetime-local" step="1" required>')}
          ${field('note', 'Osservazioni tecniche', '<textarea id="note" maxlength="280" rows="2"></textarea>', true)}
        </div>
        <p class="notice">Per le serie continue riporta il prezzo esatto del grafico: il contratto effettivo e l’eventuale adeguamento possono non essere noti.</p>
        <div class="actions">${button('send', 'Registra livello', { type: 'submit', modifier: '', disabled: true })}</div>
      </form>
    </section>
    ${dataPanel({ title: 'Le mie ricevute', name: 'myRead', prefix: 'my', heading: 'Caricamento ricevute…', hidden: !read })}
  </div>`;
}

function ownerAccessForm(id, title, label, text = '') {
  return `<form class="panel" id="${id}" autocomplete="off" aria-labelledby="${id}Heading">
    <h2 id="${id}Heading">${title}</h2>
    <div class="fields">
      ${controls(`${id}Slot`, 'Slot', [], { wide: true, placeholder: 'Seleziona slot' })}
      ${text}
    </div>
    ${status(`${id}Status`)}
    <div class="actions">${button(`${id}Send`, label, { type: 'submit', modifier: id === 'revoke' ? 'danger' : '', disabled: true })}</div>
  </form>`;
}

function ownerLevels(write, read) {
  return `${hero('Desk livelli', 'Esamina le proposte, registra le decisioni e gestisci gli accessi dei collaboratori.')}
  ${write ? '' : '<p class="notice">Registro in sola lettura.</p>'}
  <section class="panel" aria-labelledby="telegramHeading">
    <h2 id="telegramHeading">Invio livelli Telegram</h2>
    <p>SMF PLUS · Invio automatico dei nuovi livelli validi, senza approvazione.</p>
    ${status('telegramStatus','Verifica stato…')}
    <div class="actions">
      ${button('telegramToggle','Caricamento…',{disabled:true})}
      ${button('telegramReload','Aggiorna stato')}
      ${button('telegramRecover','Recupera un invio recente',{disabled:true})}
    </div>
    ${status('telegramRecoveryStatus','Recupero solo per invii mai tentati negli ultimi 15 minuti.')}
    <p class="notice">La riattivazione non pubblica lo storico. Un invio già in corso può concludersi dopo lo stop.</p>
  </section>
  <div class="work-grid">
    ${dataPanel({ title: 'Proposte da esaminare', name: 'ownerRead', prefix: 'queue', heading: 'Caricamento proposte…', hidden: !read })}
    <form class="panel" id="review" autocomplete="off" ${write ? '' : 'hidden'} aria-labelledby="reviewHeading">
      <h2 id="reviewHeading">Decisione OWNER</h2>
      <div class="fields">
        ${field('entry', 'Numero ricevuta', '<input id="entry" type="number" min="1" step="1" required>')}
        ${controls('decision', 'Decisione', [['APPROVED', 'Approva'], ['REJECTED', 'Rifiuta']], { placeholder: 'Seleziona decisione' })}
        ${field('reason', 'Motivazione per il registro OWNER', '<textarea id="reason" maxlength="280" rows="2" required></textarea>', true)}
      </div>
      ${status('reviewStatus')}
      <div class="actions">${button('reviewSend', 'Registra decisione', { type: 'submit', modifier: '', disabled: true })}</div>
    </form>
  </div>
  ${dataPanel({ title: 'Cronologia decisioni', name: 'historyPanel', prefix: 'history', heading: 'Consulta le decisioni archiviate.', hidden: !read })}
  ${dataPanel({ title: 'Collaboratori', name: 'slotsPanel', prefix: 'slots', heading: 'Caricamento slot…', hidden: !read })}
  ${write ? `<div class="access-forms">
    ${ownerAccessForm('invite', 'Invita collaboratore', 'Registra invito', field('inviteEmail', 'Email usata con Google Access', '<input id="inviteEmail" type="email" inputmode="email" maxlength="254" autocomplete="off" required>', true))}
    ${ownerAccessForm('withdraw', 'Ritira invito', 'Ritira invito')}
    ${ownerAccessForm('revoke', 'Revoca accesso', 'Revoca accesso')}
  </div>` : ''}
  ${dataPanel({ title: 'Audit OWNER', name: 'auditPanel', prefix: 'audit', heading: 'Consulta gli eventi registrati.', hidden: !read })}`;
}

export function renderContributorsPageV110(path, profile) {
  const { role, slot, can_read: read, can_write: write } = profile ?? {};
  if (path === '/join/' && role === 'INVITED' && ['friend-b', 'friend-c'].includes(slot)) {
    return shell({ role, slot, home: '/join/', caption: 'Invito Contributors', navigation: '', script: true, write: write === true,
      body: `${hero('Completa l’accesso Contributors', `Account Google verificato. Invito riservato allo slot ${slot}.`)}
      <section class="panel" aria-labelledby="enrollHeading">
        <h2 id="enrollHeading">Attiva il tuo slot</h2>
        ${status('enrollStatus', write ? '' : 'La registrazione è temporaneamente in sola lettura.')}
        <div class="actions">${button('enrollSend', 'Accetta invito', { modifier: '', disabled: true })}</div>
        <p><a id="enrollDashboard" class="nav-link" href="/contributors/" hidden>Apri la dashboard</a></p>
      </section>` });
  }
  const owner = role === 'OWNER' && slot === 'owner';
  if (!owner && (role !== 'CONTRIBUTOR' || !SLOTS.includes(slot))) return null;
  const home = owner ? '/owner/' : '/contributors/';
  const levels = path === `${home}levels/`;
  if (path !== home && !levels) return null;
  const label = owner ? 'Desk livelli' : 'I miei livelli';
  const caption = levels ? label : owner ? 'Centro di controllo' : 'Segui le tracce istituzionali';
  return shell({ role, home, slot, caption, write: write === true, navigation: navigation(home, label, levels), script: levels,
    body: levels ? (owner ? ownerLevels(write === true, read === true) : contributorLevels(write === true, read === true))
      : `${hero(caption, 'Consulta il posizionamento aggregato CFTC.')}${COT_ARCHIVE_V110}` });
}
