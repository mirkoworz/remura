const marketNumber = new Intl.NumberFormat("it-IT", {
  maximumFractionDigits: 2,
});
const signedNumber = new Intl.NumberFormat("it-IT", {
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
});
const reportDate = new Intl.DateTimeFormat("it-IT", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const captureTime = new Intl.DateTimeFormat("it-IT", {
  dateStyle: "short",
  timeStyle: "medium",
  timeZone: "Europe/Rome",
});
const marketSymbol = /^[A-Z0-9]{3,8}$/;

function element(tag, content, className) {
  const node = document.createElement(tag);
  if (content !== undefined) node.textContent = content;
  if (className) node.className = className;
  return node;
}

function formatDate(value) {
  return reportDate.format(new Date(value + "T00:00:00Z"));
}

function formatCapture(value) {
  return captureTime.format(new Date(value));
}

function change(value) {
  return signedNumber.format(value) + " pp";
}

function position(value) {
  return signedNumber.format(value) + "%";
}

function compareChanges(first, second) {
  if (first === 0 && second === 0) return "Entrambe invariate";
  if (first === 0 || second === 0) return "Una invariata";
  return Math.sign(first) === Math.sign(second) ? "Concordi" : "Opposte";
}

function isDate(value) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    Number.isFinite(Date.parse(value));
}

function isUtcTime(value) {
  return typeof value === "string" &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(value) &&
    Number.isFinite(Date.parse(value));
}

function marketGroup(title, label, headings, rows) {
  const section = element("section", undefined, "market-group");
  section.append(element("h3", title));
  if (label) section.append(element("p", label, "muted"));

  const scroll = element("div", undefined, "table-scroll");
  scroll.tabIndex = 0;
  scroll.setAttribute("role", "region");
  scroll.setAttribute("aria-label", title);

  const table = element("table");
  const header = table.createTHead().insertRow();
  for (const heading of headings) {
    const cell = element("th", heading);
    cell.scope = "col";
    header.append(cell);
  }

  const body = table.createTBody();
  const searchableRows = rows.map(({ key, cells }) => {
    const row = body.insertRow();
    const symbol = element("th", cells[0]);
    symbol.scope = "row";
    row.append(symbol);
    for (const value of cells.slice(1)) row.insertCell().textContent = value;
    return { key, row };
  });
  scroll.append(table);
  section.append(scroll);
  return { section, searchableRows };
}

function filterGroups(labelText, groups, resultName) {
  const panel = element("div", undefined, "market-filter");
  const label = element("label", labelText);
  const search = element("input");
  search.type = "search";
  search.autocomplete = "off";
  search.spellcheck = false;
  label.append(search);
  const status = element("p", undefined, "muted");
  status.setAttribute("role", "status");
  panel.append(label, status);

  const total = groups.reduce((count, group) => count + group.searchableRows.length, 0);
  function update() {
    const query = search.value.toUpperCase().replace(/[\s/.-]/g, "");
    let visible = 0;
    for (const { section, searchableRows } of groups) {
      let groupVisible = 0;
      for (const { key, row } of searchableRows) {
        const match = key.includes(query);
        row.hidden = !match;
        if (match) groupVisible++;
      }
      section.hidden = groupVisible === 0;
      visible += groupVisible;
    }
    status.textContent = visible === 0 ? "Nessun risultato." : `${visible} di ${total} ${resultName}`;
  }
  search.addEventListener("input", update);
  update();
  return [panel, ...groups.map(({ section }) => section)];
}

function factorRow(factor) {
  const {
    currency, cftcContractCode, assetManagerNetPctOi, leveragedFundsNetPctOi,
    weeklyAssetManagerChangePp, weeklyLeveragedFundsChangePp,
    openInterestContracts, openInterestChangeContracts,
  } = factor;
  if (!/^[A-Z]{3}$/.test(currency) || !/^[A-Z0-9]{6}$/.test(cftcContractCode) ||
      ![assetManagerNetPctOi, leveragedFundsNetPctOi, weeklyAssetManagerChangePp,
        weeklyLeveragedFundsChangePp, openInterestContracts, openInterestChangeContracts].every(Number.isFinite)) {
    throw new Error("Riga dei fattori COT non valida");
  }
  return {
    key: `${currency} ${cftcContractCode}`,
    cells: [
      currency, cftcContractCode, position(assetManagerNetPctOi),
      change(weeklyAssetManagerChangePp), position(leveragedFundsNetPctOi),
      change(weeklyLeveragedFundsChangePp),
      compareChanges(weeklyAssetManagerChangePp, weeklyLeveragedFundsChangePp),
      marketNumber.format(openInterestContracts),
      signedNumber.format(openInterestChangeContracts),
    ],
  };
}

function crossRow(cross) {
  const {
    symbol, assetManagerWeeklyRelativeChangePp, leveragedFundsWeeklyRelativeChangePp,
    derivedNotDirectSpot,
  } = cross;
  if (!marketSymbol.test(symbol) || derivedNotDirectSpot !== true ||
      ![assetManagerWeeklyRelativeChangePp, leveragedFundsWeeklyRelativeChangePp].every(Number.isFinite)) {
    throw new Error("Riga dei cross COT non valida");
  }
  return {
    key: symbol,
    cells: [
      symbol,
      change(assetManagerWeeklyRelativeChangePp),
      change(leveragedFundsWeeklyRelativeChangePp),
      compareChanges(assetManagerWeeklyRelativeChangePp, leveragedFundsWeeklyRelativeChangePp),
    ],
  };
}

function futuresRow(entry) {
  const { symbol, codes, netA_Pp, netB_Pp, deltaA_Pp, deltaB_Pp, referenceType } = entry;
  if (!marketSymbol.test(symbol) || referenceType !== "futures_reference" ||
      !Array.isArray(codes) || !codes.length || !codes.every(code => /^[A-Z0-9]{6}$/.test(code)) ||
      ![netA_Pp, netB_Pp, deltaA_Pp, deltaB_Pp].every(Number.isFinite)) {
    throw new Error("Riga dei futures COT non valida");
  }
  return {
    key: [symbol, ...codes].join(" "),
    cells: [
      symbol, codes.join(", "), position(netA_Pp), change(deltaA_Pp),
      position(netB_Pp), change(deltaB_Pp), compareChanges(deltaA_Pp, deltaB_Pp),
    ],
  };
}

function futuresGroup(sets, dataset, title, label, categoryA, categoryB) {
  const group = sets.find(set => set.dataset === dataset);
  if (!group?.entries?.length ||
      !group.entries.every(entry => entry.categoryA === categoryA && entry.categoryB === categoryB)) {
    throw new Error("Categorie dei futures COT non valide");
  }
  return marketGroup(title, label, [
    "Mercato di riferimento", "Codice CFTC", `${categoryA} · netto`, `${categoryA} · Δ`,
    `${categoryB} · netto`, `${categoryB} · Δ`, "Confronto Δ",
  ], group.entries.map(futuresRow));
}

function renderCot(snapshot) {
  const { dashboard, directFutures, publicReadAtUtc } = snapshot;
  if (snapshot.schema !== "remura-b-v223-public-export-only-v1" ||
      dashboard?.mode !== "descriptive_only" || !Array.isArray(dashboard.factors) ||
      !Array.isArray(dashboard.crosses) || !Array.isArray(directFutures) ||
      !isDate(dashboard.latestCftcReportDate) || !isDate(dashboard.previousCftcReportDate) ||
      !isUtcTime(publicReadAtUtc)) {
    throw new Error("Archivio COT non valido");
  }

  const groups = [
    marketGroup("Fattori valutari", "CFTC TFF · Futures Only", [
      "Valuta", "Codice CFTC", "Asset Manager · netto", "Asset Manager · Δ",
      "Leveraged Funds · netto", "Leveraged Funds · Δ", "Confronto Δ", "Open interest", "Open interest · Δ",
    ], dashboard.factors.map(factorRow)),
    marketGroup("Cross valutari sintetici",
      "Differenza tra i fattori futures delle due valute. USD è il riferimento matematico.",
      ["Cross", "Asset Manager · Δ relativo", "Leveraged Funds · Δ relativo", "Confronto Δ"],
      dashboard.crosses.map(crossRow)),
    futuresGroup(directFutures, "tff", "Futures finanziari", "CFTC TFF · Futures Only",
      "Asset Manager/Institutional", "Leveraged Funds"),
    futuresGroup(directFutures, "disagg", "Futures su materie prime", "CFTC Disaggregated · Futures Only",
      "Managed Money", "Producer/Merchant"),
  ];
  return [
    element("p",
      `Archivio CFTC acquisito il ${formatCapture(publicReadAtUtc)} (ora italiana). ` +
      `Report settimanali del ${formatDate(dashboard.latestCftcReportDate)} e ${formatDate(dashboard.previousCftcReportDate)}.`,
      "notice"),
    element("p",
      "Il netto è una quota dell’open interest e il suo Δ settimanale è in punti percentuali (pp). " +
      "L’open interest è espresso in contratti. " +
      "L’estratto contiene due settimane. Indice a 52 settimane N/D.",
      "muted"),
    ...filterGroups("Cerca per simbolo, valuta o codice CFTC", groups, "righe COT"),
  ];
}

function validRetailEntry([symbol, row]) {
  return marketSymbol.test(symbol) && row && isUtcTime(row.t) &&
    [row.lPct, row.sPct].every(value => Number.isFinite(value) && value >= 0 && value <= 100);
}

function renderRetail(snapshot) {
  if (snapshot.status !== "ok" || snapshot.source !== "Myfxbook Community Outlook" ||
      !isUtcTime(snapshot.updatedAt) || !snapshot.symbols || typeof snapshot.symbols !== "object" ||
      Array.isArray(snapshot.symbols)) {
    throw new Error("Archivio Myfxbook non valido");
  }

  const rows = Object.entries(snapshot.symbols).filter(validRetailEntry).sort(([a], [b]) => a.localeCompare(b));
  if (!rows.length) throw new Error("Nessun mercato Myfxbook valido");
  const group = marketGroup("Campione retail per mercato", "",
    ["Simbolo", "Long", "Short", "Rilevazione (ora italiana)"],
    rows.map(([symbol, row]) => ({
      key: symbol,
      cells: [symbol, marketNumber.format(row.lPct) + "%", marketNumber.format(row.sPct) + "%", formatCapture(row.t)],
    })));

  return [
    element("p", `Archivio Myfxbook Community Outlook acquisito il ${formatCapture(snapshot.updatedAt)} (ora italiana).`,
      "notice"),
    element("p", "Long e short sono quote del volume in lotti del campione retail Myfxbook.", "muted"),
    ...filterGroups("Cerca per simbolo", [group], "mercati"),
  ];
}

async function loadMarketArchive(root, filename, render) {
  root.setAttribute("aria-busy", "true");
  root.replaceChildren(element("p", "Caricamento dell’archivio…", "muted"));
  try {
    const response = await fetch(new URL(`./data/${filename}`, import.meta.url), { mode: "same-origin" });
    if (!response.ok) throw new Error("Archivio non disponibile");
    root.replaceChildren(...render(await response.json()));
    return true;
  } catch {
    const error = element("p", "Archivio non disponibile. Ricarica la pagina per riprovare.", "notice");
    error.setAttribute("role", "status");
    root.replaceChildren(error);
    return false;
  } finally {
    root.removeAttribute("aria-busy");
  }
}

export async function mountMarkets(cotRoot, retailRoot) {
  const [cot, retail] = await Promise.all([
    loadMarketArchive(cotRoot, "cot-b223.json", renderCot),
    loadMarketArchive(retailRoot, "myfxbook-latest.json", renderRetail),
  ]);
  return { cot, retail };
}
