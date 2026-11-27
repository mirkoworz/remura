function browserTools() {
  const find = id => document.getElementById(id);
  const observedUtc = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  // Fixed Europe/Rome timezone even if the device is abroad. Reject DST gaps/folds.
  const romeFormat = new Intl.DateTimeFormat('en-CA', {timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
  function romeLocal(date) {
    const parts=Object.fromEntries(romeFormat.formatToParts(date).map(x=>[x.type,x.value]));
    return parts.year+'-'+parts.month+'-'+parts.day+'T'+parts.hour+':'+parts.minute+':'+parts.second;
  }
  function romeToUtc(value) {
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) value+=':00';
    if (!/^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(value)) throw Error('rome_date');
    const nominal=Date.parse(value+'Z');
    if(!Number.isFinite(nominal)) throw Error('rome_date');
    const matches=[60,120].map(m=>new Date(nominal-m*60000)).filter(d=>romeLocal(d)===value);
    if(matches.length!==1)throw Error('rome_date_ambiguous_or_invalid');
    return matches[0].toISOString().replace('.000Z','Z');
  }
  const observedRome=()=>romeLocal(new Date());
  const oneLine = text => text.replace(/\r\n?|\n/g, ' ');
  const stateLabels = {
    UNREVIEWED: 'In attesa', APPROVED: 'Approvato', REJECTED: 'Rifiutato',
    ACTIVE: 'Attivo', REVOKED: 'Revocato', INVITED: 'Invito in attesa', AVAILABLE: 'Disponibile',
    WITHDRAWN: 'Invito ritirato', ENROLLED: 'Iscrizione completata',
  };

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function status(id, text, tone = '') {
    const el = find(id);
    el.textContent = text;
    el.dataset.tone = tone;
  }

  function state(value, label = stateLabels[value] ?? value) {
    const node = element('span', label, 'state');
    node.dataset.state = value;
    return node;
  }

  function choices(id, values, placeholder) {
    const select = find(id);
    const previous = select.value;
    const option = ([value, label]) => {
      const node = element('option', label);
      node.value = value;
      return node;
    };
    select.replaceChildren(option(['', placeholder]), ...values.map(option));
    if (values.some(([value]) => value === previous)) select.value = previous;
  }

  function displayDate(value) {
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) return value;
    return new Intl.DateTimeFormat('it-IT', {
      timeZone: 'Europe/Rome', dateStyle: 'short', timeStyle: 'medium',
    }).format(date);
  }

  async function request(path, options = {}) {
    const { body, intent, requestId } = options;
    const headers = new Headers({ Accept: 'application/json' });
    if (body !== undefined) {
      headers.set('Content-Type', 'application/json');
      headers.set('X-Remura-CSRF', '1');
    }
    if (intent) headers.set('X-Remura-Intent', intent);
    if (requestId) headers.set('X-Remura-Request-ID', requestId);
    const timeout = new AbortController();
    const timer = setTimeout(() => timeout.abort(), 15000);
    try {
      const response = await fetch(path, {
        method: body === undefined ? 'GET' : 'POST', body: body === undefined ? undefined : JSON.stringify(body),
        headers, credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: timeout.signal,
      });
      if (!/^application\/json\b/i.test(response.headers.get('Content-Type') ?? '')) {
        throw Object.assign(new Error('non_json'), { status: response.status });
      }
      const data = await response.json();
      if (!response.ok) throw Object.assign(new Error('request_failed'), { code: data.error, status: response.status });
      return data;
    } finally {
      clearTimeout(timer);
    }
  }

  async function mutation(path, body) {
    const { intent } = await request('/api/intent', { body: { path, body } });
    if (typeof intent !== 'string' || !intent) throw new Error('intent_missing');
    try {
      return await request(path, { body, intent });
    } catch (error) {
      throw Object.assign(error, { dispatched: true });
    }
  }

  function paginator({ prefix, endpoint, empty, render }) {
    const loadButton = find(`${prefix}Load`);
    const nextButton = find(`${prefix}Next`);
    let cursor = null;
    async function load(after = 0) {
      if (loadButton.disabled) return;
      loadButton.disabled = nextButton.disabled = true;
      try {
        const { items, next } = await request(`${endpoint}?after=${after}`);
        if (!Array.isArray(items) || (next !== null && (!Number.isSafeInteger(next) || next <= after))) {
          throw new Error('invalid_page');
        }
        render(find(`${prefix}Rows`), items);
        cursor = next;
        nextButton.hidden = cursor === null;
        status(`${prefix}Status`, items.length ? '' : empty);
      } catch (error) {
        if ([401, 403].includes(error.status)) {
          find(`${prefix}Rows`).replaceChildren();
          cursor = null;
          nextButton.hidden = true;
        }
        status(`${prefix}Status`, 'Lettura non disponibile. Aggiorna per riprovare.', 'error');
      } finally {
        loadButton.disabled = nextButton.disabled = false;
      }
    }
    loadButton.addEventListener('click', () => load());
    nextButton.addEventListener('click', () => { if (cursor !== null) void load(cursor); });
    return { load };
  }

  function table(container, caption, headers, rows) {
    container.replaceChildren();
    if (!rows.length) return;
    const scroll = element('div', undefined, 'scroll');
    scroll.tabIndex = 0;
    scroll.setAttribute('role', 'region');
    scroll.setAttribute('aria-label', caption);
    const grid = element('table', undefined, 'work-table');
    const thead = grid.createTHead();
    const labels = thead.insertRow();
    for (const header of headers) {
      const cell = element('th', header);
      cell.scope = 'col';
      labels.append(cell);
    }
    const tbody = grid.createTBody();
    for (const values of rows) {
      const row = tbody.insertRow();
      for (const [index, value] of values.entries()) {
        const cell = element(index ? 'td' : 'th');
        if (!index) cell.scope = 'row';
        cell.append(value instanceof Node ? value : document.createTextNode(String(value ?? '—')));
        row.append(cell);
      }
    }
    scroll.append(grid);
    container.append(scroll);
  }

  function receipt(row, forOwner = false) {
    const details = element('details', undefined, 'receipt');
    const summary = element('summary');
    const marker = element('span', undefined, 'chevron');
    marker.setAttribute('aria-hidden', 'true');
    summary.append(element('span', `#${row.id} · ${row.market} · ${row.price}`), state(row.status), marker);
    const mapping = row.contract==='CONTINUOUS' ? `${row.provider} · ${row.ticker.replace(/_CONT$/,'')} · Grafico continuativo (scadenza/adeguamento non verificati)` : [row.provider, row.ticker, row.product, row.contract].filter(Boolean).join(' · ');
    const periods = { DAY: 'Giorno', WEEK: 'Settimana', CURRENT_MONTH: 'Mese corrente', PREVIOUS_MONTH: 'Mese precedente' };
    const methods = { DELTA_PEAK: 'Picco delta', EFFORT_RESULT: 'Effort / result', OTHER_VOLUME_LEVEL: 'Altro livello volumetrico' };
    const values = [
      ['Strumento e fonte', mapping], ['Periodo', periods[row.period] ?? row.period],
      ['Metodologia', methods[row.kind] ?? row.kind], ['Riferimento (Roma)', displayDate(row.anchor_utc)],
      ['Osservato (Roma)', displayDate(row.observed_utc)], ['Ricevuto (Roma)', displayDate(row.received_utc)],
      ['Decisione (Roma)', row.reviewed_utc && displayDate(row.reviewed_utc)], ['Osservazioni', row.note],
    ];
    if (forOwner) values.unshift(['Slot', row.slot]);
    const fields = element('dl');
    for (const [label, value] of values) {
      if (value) fields.append(element('dt', label), element('dd', value));
    }
    details.append(summary, fields);
    return details;
  }

  function protectPage() {
    window.addEventListener('pageshow', event => {
      if (event.persisted) window.location.reload();
    });
  }

  return { find, observedUtc, observedRome, romeToUtc, oneLine, element, status, state, choices, displayDate, request, mutation, paginator, table, receipt, protectPage };
}

function startContributor({ find, observedRome, romeToUtc, oneLine, status, choices, request, mutation, paginator, receipt, protectPage }) {
  protectPage();
  const write = document.body.dataset.write === 'true';
  const storageKey = `remura.contributors.v110.pending.${document.body.dataset.slot}`;
  const idPattern = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
  const digestPattern = /^[a-f0-9]{64}$/;
  const form = find('intake');
  const catalogButton = find('catalogLoad');
  const intakeLabel = find('send').textContent;
  const receiptPager = paginator({
    prefix: 'my', endpoint: '/api/receipts', empty: 'Nessuna ricevuta in questa pagina.',
    render: (container, rows) => container.replaceChildren(...rows.map(row => receipt(row))),
  });
  let catalog = [];
  let busy = false;
  let pending = readPending();
  let original = null;
  let absent = false;

  function readPending() {
    try {
      const saved = JSON.parse(sessionStorage.getItem(storageKey));
      if (saved && idPattern.test(saved.id) && digestPattern.test(saved.digest)) return saved;
    } catch {
      // A new dispatch will validate tab storage before contacting the server.
    }
    return null;
  }

  function clearPending() {
    pending = null;
    original = null;
    absent = false;
    try { sessionStorage.removeItem(storageKey); } catch {
      // The server result is authoritative if the stored reference reappears.
    }
  }

  async function draftDigest(data) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(data)));
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  }

  function decisions() {
    const reenter = pending && absent && !original;
    form.hidden = !write || !catalog.length || Boolean(pending && !reenter);
    find('send').textContent = reenter ? 'Reinvia lo stesso livello' : intakeLabel;
    find('send').disabled = busy || form.hidden;
    find('pendingAttempt').hidden = !pending;
    find('checkAttempt').disabled = busy;
    find('retryAttempt').hidden = !write || !pending || !absent || !original;
    find('retryAttempt').disabled = busy;
    find('clearAttempt').hidden = !pending || !absent;
    find('clearAttempt').disabled = busy;
    if (pending) {
      find('pendingMessage').textContent = absent
        ? 'La ricevuta non è ancora presente. Puoi riprovare con gli stessi dati e la stessa richiesta. L’invio iniziale potrebbe ancora arrivare.'
        : 'La proposta potrebbe essere già stata registrata. Verifica la ricevuta prima di riprovare.';
    }
  }

  function updateMappings() {
    const market = find('market').value;
    const provider = find('provider').value;
    choices('mapping', catalog.flatMap((row, index) => row.market === market && row.provider === provider
      ? [[String(index), row.contract==='CONTINUOUS' ? `${row.ticker.replace(/_CONT$/,'')} · Grafico continuativo` : [row.ticker, row.product, row.contract].filter(Boolean).join(' · ')]] : []), 'Seleziona serie');
  }

  function updateProviders() {
    const providers = new Set(catalog.filter(row => row.market === find('market').value).map(row => row.provider));
    choices('provider', [...providers].map(value => [value, value]), 'Seleziona fonte');
    updateMappings();
  }

  async function loadCatalog() {
    catalogButton.hidden = true;
    status('catalogStatus', 'Caricamento catalogo…');
    try {
      const { items } = await request('/api/catalog');
      const fields = ['market', 'provider', 'ticker', 'product', 'contract'];
      if (!Array.isArray(items) || !items.every(row => row && fields.every(field => typeof row[field] === 'string'))) {
        throw new Error('invalid_catalog');
      }
      catalog = items;
      find('mapping').value = '';
      choices('market', [...new Set(catalog.map(row => row.market))].map(value => [value, value]), 'Seleziona strumento');
      updateProviders();
      status('catalogStatus', catalog.length ? '' : 'Nessuna fonte abilitata per l’invio.', catalog.length ? '' : 'warning');
      catalogButton.hidden = catalog.length > 0;
    } catch {
      status('catalogStatus', 'Catalogo non disponibile. Ricarica per riprovare.', 'error');
      catalogButton.hidden = false;
    } finally {
      decisions();
    }
  }

  function draft(id) {
    const selection = find('mapping').value;
    const row = selection === '' ? null : catalog[Number(selection)];
    if (!row || row.market !== find('market').value || row.provider !== find('provider').value) throw new Error('mapping');
    let price = find('price').value.trim().replace(',', '.');
    if (price.includes('.')) price = price.replace(/0+$/, '').replace(/\.$/, '');
    return {
      request_id: id, market: row.market, provider: row.provider, ticker: row.ticker, product: row.product,
      contract: row.contract, period: find('period').value, kind: find('kind').value, price,
      anchor_utc: romeToUtc(find('anchor').value), observed_utc: romeToUtc(find('observed').value), note: oneLine(find('note').value),
    };
  }

  function confirmReceipt(result) {
    if (!['COMMITTED', 'DUPLICATE'].includes(result.state) || !Number.isSafeInteger(result.receipt?.id) || result.receipt.id < 1) {
      return false;
    }
    const label = result.state === 'DUPLICATE' ? 'Livello già registrato (nessuna nuova pubblicazione)' : 'Proposta registrata';
    status('intakeStatus', `${label} · Ricevuta #${result.receipt.id}.`, 'success');
    clearPending();
    form.reset();
    updateProviders();
    find('observed').value = observedRome();
    if (!find('myRead').hidden) void receiptPager.load();
    return true;
  }

  async function dispatch(data, existing) {
    absent = false;
    decisions();
    status('intakeStatus', 'Invio della proposta…');
    try {
      const result = await mutation('/api/submit', data);
      if (!confirmReceipt(result)) throw Object.assign(new Error('invalid_receipt'), { dispatched: true });
    } catch (error) {
      const known = ['invalid', 'invalid_mapping', 'conflict', 'denied', 'capacity'].includes(error.code);
      if ((!error.dispatched || known) && !existing) {
        clearPending();
        const messages = {
          invalid: 'Dati rifiutati. Controlla i campi e la cronologia UTC.',
          invalid_mapping: 'Strumento e fonte non disponibili. Ricarica il catalogo.',
          conflict: 'Proposta in conflitto con un tentativo registrato. Aggiorna le ricevute.',
          denied: 'Invio rifiutato. Verifica i permessi e ricarica la pagina.',
          capacity: 'Limite di invii raggiunto.',
        };
        if (error.code === 'invalid_mapping') {
          catalog = [];
          catalogButton.hidden = false;
        }
        const message = messages[error.code] ?? 'Invio non avviato. Riprova quando la connessione è disponibile.';
        status('intakeStatus', message, 'error');
      } else {
        status('intakeStatus', 'Esito dell’invio incerto.', 'warning');
      }
    }
  }

  async function exclusive(fn) {
    if (busy) return;
    busy = true;
    decisions();
    try { await fn(); } finally {
      busy = false;
      decisions();
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!write || form.hidden || busy) return;
    void exclusive(async () => {
      const existing = Boolean(pending);
      let data;
      let digest;
      try {
        data = draft(pending?.id ?? crypto.randomUUID());
        digest = await draftDigest(data);
      } catch {
        status('intakeStatus', 'Impossibile preparare la richiesta. Controlla i campi e l’ora di Roma (evita ore ambigue del cambio legale).', 'error');
        return;
      }
      if (pending && digest !== pending.digest) {
        status('intakeStatus', 'I dati differiscono dalla proposta da verificare. Ricontrolla anche le due date UTC e le osservazioni.', 'error');
        return;
      }
      if (!pending) {
        try {
          const reference = { id: data.request_id, digest };
          sessionStorage.setItem(storageKey, JSON.stringify(reference));
          pending = reference;
        } catch {
          status('intakeStatus', 'La scheda non può salvare il riferimento per verificare l’invio.', 'error');
          return;
        }
      }
      original = Object.freeze(data);
      await dispatch(original, existing);
    });
  });

  find('checkAttempt').addEventListener('click', () => void exclusive(async () => {
    if (!pending) return;
    status('intakeStatus', 'Verifica in corso…');
    try {
      const result = await request('/api/level-attempt/status', { requestId: pending.id });
      if (confirmReceipt(result)) return;
      if (result.state !== 'NOT_FOUND') throw new Error('invalid_attempt');
      absent = true;
      status('intakeStatus', original || !write ? '' : 'Ricompila la proposta precedente con gli stessi valori prima di reinviarla.', 'warning');
    } catch {
      absent = false;
      status('intakeStatus', 'Impossibile verificare il tentativo. Riprova quando la connessione è disponibile.', 'error');
    }
  }));
  find('retryAttempt').addEventListener('click', () => {
    if (pending && absent && original && write) void exclusive(() => dispatch(original, true));
  });
  find('clearAttempt').addEventListener('click', () => {
    if (!pending || !absent || busy) return;
    if (!window.confirm('La proposta iniziale potrebbe ancora arrivare. Vuoi chiudere la verifica e preparare una nuova proposta?')) return;
    clearPending();
    form.reset();
    updateProviders();
    find('observed').value = observedRome();
    status('intakeStatus', 'Verifica chiusa. Aggiorna le ricevute per controllare eventuali registrazioni successive.', 'warning');
    decisions();
  });
  find('market').addEventListener('change', updateProviders);
  find('provider').addEventListener('change', updateMappings);
  catalogButton.addEventListener('click', () => void loadCatalog());
  find('observed').value = observedRome();
  decisions();
  if (write) void loadCatalog();
  if (!find('myRead').hidden) void receiptPager.load();
}

function startOwner({ find, oneLine, element, status, state, choices, displayDate, request, mutation, paginator, table, receipt, protectPage }) {
  protectPage();
  const write = document.body.dataset.write === 'true';
  const slotButtons = ['inviteSend', 'withdrawSend', 'revokeSend'];
  const slotsLoad = find('slotsLoad');
  const inviteEmail = find('inviteEmail');
  const reviewForm = find('review');
  let mutating = false;
  let slots = [];
  const telegramToggle=find('telegramToggle');
  const telegramReload=find('telegramReload');
  const telegramRecover=find('telegramRecover');
  let telegramPolicy=null,telegramBusy=false;
  function renderTelegram(){
    telegramToggle.disabled=telegramBusy||!write||!telegramPolicy||(!telegramPolicy.enabled&&!telegramPolicy.configured);
    telegramReload.disabled=telegramBusy;
    telegramRecover.disabled=telegramBusy||!write||telegramPolicy?.enabled!==1||!telegramPolicy.configured;
    telegramToggle.textContent=!telegramPolicy?'Stato non disponibile':telegramPolicy.enabled?'Disabilita invio livelli Telegram':'Abilita invio livelli Telegram';
    telegramToggle.setAttribute('aria-pressed',String(telegramPolicy?.enabled===1));
  }
  async function loadTelegram(){
    telegramPolicy=null;
    renderTelegram();
    try{
      const p=await request('/owner/telegram/status');
      if(![0,1].includes(p.enabled)||!Number.isSafeInteger(p.epoch)||p.epoch<1||typeof p.configured!=='boolean')throw Error('telegram');
      telegramPolicy=p;
      status('telegramStatus',p.enabled?(p.configured?'Invio automatico abilitato':'Abilitato, configurazione non disponibile'):'Invio automatico disabilitato'+(p.configured?'':' · Configurazione non disponibile'),p.enabled&&p.configured?'success':'warning');
    }catch{status('telegramStatus','Stato Telegram non disponibile. Aggiorna per riprovare.','warning');}
    renderTelegram();
  }
  telegramReload.addEventListener('click',async()=>{
    if(telegramBusy)return;telegramBusy=true;renderTelegram();
    try{await loadTelegram();}finally{telegramBusy=false;renderTelegram();}
  });
  telegramToggle.addEventListener('click',async()=>{
    if(telegramToggle.disabled||telegramBusy||!telegramPolicy)return;
    const body={enabled:telegramPolicy.enabled===0,epoch:telegramPolicy.epoch};
    if(body.enabled&&!window.confirm('Abilitare l’invio automatico dei nuovi livelli a SMF PLUS?'))return;
    telegramBusy=true;renderTelegram();
    try{await mutation('/owner/telegram/toggle',body);}
    catch{status('telegramStatus','Modifica non confermata. Verifica lo stato prima di riprovare.','warning');}
    finally{await loadTelegram();telegramBusy=false;renderTelegram();}
  });
  telegramRecover.addEventListener('click',async()=>{
    if(telegramRecover.disabled||telegramBusy||!telegramPolicy)return;
    if(!window.confirm('Recuperare un livello recente mai inviato a SMF PLUS?'))return;
    const body={epoch:telegramPolicy.epoch};
    telegramBusy=true;renderTelegram();
    try{
      const r=await mutation('/owner/telegram/recover',body);
      const labels={SENT:'Consegna Telegram confermata.',EMPTY:'Nessun invio recente da recuperare.',BLOCKED:'Invio bloccato dalle protezioni.',OFF:'Telegram non configurato.'};
      status('telegramRecoveryStatus',labels[r.state]??'Esito incerto: non ripetere il medesimo invio.',r.state==='SENT'?'success':'warning');
    }catch{status('telegramRecoveryStatus','Esito non confermato. Controlla il gruppo prima di proseguire.','warning');}
    finally{await loadTelegram();telegramBusy=false;renderTelegram();}
  });
  telegramBusy=true;
  void loadTelegram().finally(()=>{telegramBusy=false;renderTelegram();});

  const queue = paginator({
    prefix: 'queue', endpoint: '/owner/queue', empty: 'Nessuna proposta da esaminare in questa pagina.',
    render(container, rows) {
      container.replaceChildren(...rows.map(row => {
        const card = receipt(row, true);
        if (write && row.status === 'UNREVIEWED') {
          const actions = element('div', undefined, 'actions receipt-actions');
          const select = element('button', `Esamina #${row.id}`, 'secondary');
          select.type = 'button';
          select.addEventListener('click', () => {
            if (mutating) return;
            find('entry').value = row.id;
            find('decision').focus();
          });
          actions.append(select);
          card.append(actions);
        }
        return card;
      }));
    },
  });

  function renderAudit(container, rows) {
    const actionLabels = { INVITED: 'Invito registrato', REVOKED: 'Accesso revocato' };
    table(container, 'Eventi del registro OWNER', ['Evento', 'Riferimento', 'Ora (Roma)', 'Motivazione'], rows.map(row => [
      state(row.action, actionLabels[row.action]), row.entry_id == null ? row.slot : `Ricevuta #${row.entry_id}`, displayDate(row.at_utc), row.reason || '—',
    ]));
  }

  const history = paginator({
    prefix: 'history', endpoint: '/owner/history', empty: 'Nessuna decisione in questa pagina.',
    render: (container, rows) => container.replaceChildren(...rows.map(row => receipt(row, true))),
  });
  const audit = paginator({ prefix: 'audit', endpoint: '/owner/audit', empty: 'Nessun evento in questa pagina.', render: renderAudit });
  const slotTypes = { invite: 'AVAILABLE', withdraw: 'INVITED', revoke: 'ACTIVE' };

  function refreshButtons() {
    find('reviewSend').disabled = !write || mutating;
    for (const id of slotButtons) {
      const control = find(id);
      if (!control) continue;
      const type = id.slice(0, -4);
      control.disabled = mutating || !slots.some(row => row.status === slotTypes[type] && (type !== 'invite' || row.slot !== 'friend-a'));
    }
  }

  function renderSlots() {
    table(find('slotsRows'), 'Stato degli slot', ['Slot', 'Stato'], slots.map(({ slot, status: current }) => [slot, state(current)]));
    if (write) {
      for (const [type, current] of Object.entries(slotTypes)) {
        const eligible = slots.filter(row => row.status === current && (type !== 'invite' || row.slot !== 'friend-a'));
        choices(`${type}Slot`, eligible.map(row => [row.slot, row.slot]), 'Seleziona slot');
      }
    }
    refreshButtons();
  }

  async function loadSlots() {
    if (slotsLoad.disabled) return;
    slotsLoad.disabled = true;
    try {
      const { items } = await request('/owner/collaborators');
      const allowed = ['friend-a', 'friend-b', 'friend-c'];
      const states = ['AVAILABLE', 'INVITED', 'ACTIVE', 'REVOKED'];
      if (!Array.isArray(items) || items.length !== allowed.length ||
          !allowed.every(slot => items.some(row => row?.slot === slot && states.includes(row.status)))) {
        throw new Error('invalid_slots');
      }
      slots = items;
      status('slotsStatus', '');
    } catch {
      slots = [];
      status('slotsStatus', 'Stato degli slot non disponibile. Aggiorna per riprovare.', 'error');
    } finally {
      renderSlots();
      slotsLoad.disabled = false;
    }
  }

  function logResult(prefix, error) {
    if (error.code === 'conflict') {
      status(`${prefix}Status`, 'Lo stato è cambiato. Aggiorna il registro prima di procedere.', 'error');
    } else if (error.code === 'invalid') {
      status(`${prefix}Status`, 'Verifica i dati della richiesta.', 'error');
    } else if (error.code === 'denied') {
      status(`${prefix}Status`, 'Operazione rifiutata. Verifica i permessi.', 'error');
    } else if (error.dispatched) {
      status(`${prefix}Status`, 'Esito incerto. Consulta il registro e l’audit prima di ripetere l’operazione.', 'warning');
    } else {
      status(`${prefix}Status`, 'Operazione non avviata. Riprova quando è disponibile la connessione.', 'error');
    }
  }

  async function run(prefix, path, body, success, refresh) {
    if (!write || mutating) return;
    mutating = true;
    refreshButtons();
    status(`${prefix}Status`, 'Registrazione in corso…');
    try {
      await mutation(path, body);
      status(`${prefix}Status`, success, 'success');
      find(prefix).reset();
    } catch (error) {
      logResult(prefix, error);
    } finally {
      if (prefix === 'invite') inviteEmail.value = '';
      await refresh();
      mutating = false;
      refreshButtons();
    }
  }

  reviewForm.addEventListener('submit', event => {
    event.preventDefault();
    const id = Number(find('entry').value);
    const action = find('decision').value;
    const reason = oneLine(find('reason').value).trim();
    if (!Number.isSafeInteger(id) || id < 1 || !['APPROVED', 'REJECTED'].includes(action) || !reason) {
      status('reviewStatus', 'Compila numero ricevuta, decisione e motivazione.', 'error');
      return;
    }
    void run('review', '/owner/review', { id, action, reason },
      `${action === 'APPROVED' ? 'Approvazione registrata' : 'Rifiuto registrato'} · Ricevuta #${id}.`,
      () => Promise.all([queue.load(), history.load()]));
  });

  if (write) {
    const confirmations = { invite: 'Invito registrato.', withdraw: 'Invito ritirato.', revoke: 'Accesso revocato.' };
    for (const [type, current] of Object.entries(slotTypes)) {
      find(type).addEventListener('submit', event => {
        event.preventDefault();
        const slot = find(`${type}Slot`).value;
        if (mutating || !slots.some(row => row.slot === slot && row.status === current)) return;
        if (type === 'revoke' && !window.confirm(`Revocare l’accesso Contributors per ${slot}?`)) return;
        const body = type === 'invite' ? { slot, email: inviteEmail.value.trim() } : { slot };
        void run(type, `/owner/${type}`, body, confirmations[type], loadSlots);
      });
    }
    window.addEventListener('pagehide', () => { inviteEmail.value = ''; });
  }
  slotsLoad.addEventListener('click', () => void loadSlots());
  refreshButtons();
  if (!find('ownerRead').hidden) void queue.load();
  if (!find('slotsPanel').hidden) void loadSlots();
}

function startInvited({ find, status, request, mutation, protectPage }) {
  protectPage();
  const button = find('enrollSend');
  const write = document.body.dataset.write === 'true';
  button.disabled = !write;
  button.addEventListener('click', async () => {
    if (!write || button.disabled) return;
    button.disabled = true;
    status('enrollStatus', 'Registrazione in corso…');
    let activated = false;
    try {
      await mutation('/api/enroll', {});
      activated = true;
    } catch (error) {
      if (error.dispatched || error.code === 'denied') {
        try {
          const profile = await request('/api/profile');
          activated = profile.role === 'CONTRIBUTOR' && profile.slot === document.body.dataset.slot;
        } catch {
          // Activation remains unconfirmed until another allowed profile check.
        }
      }
    } finally {
      button.disabled = activated;
      if (activated) {
        button.hidden = true;
        find('enrollDashboard').hidden = false;
        status('enrollStatus', 'Slot attivato.', 'success');
      } else {
        status('enrollStatus', 'Attivazione non confermata. Verifica l’invito con l’OWNER o riprova.', 'warning');
      }
    }
  });
}

function standalone(start) {
  return `(${start.toString()})((${browserTools.toString()})());\n`;
}

export const CONTRIBUTORS_BROWSER_V110 = Object.freeze({
  CONTRIBUTOR: standalone(startContributor),
  OWNER: standalone(startOwner),
  INVITED: standalone(startInvited),
});
