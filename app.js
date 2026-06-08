// SJTCG static card image database + local deckbuilder
let allCards = [];
let visibleCards = [];
let currentModalIndex = -1;
let modalCards = [];
let activeFilters = { release: "", set: "", color: "", type: "" };
let deck = { leader: "", main: {}, jump: {} };
let deckSortMode = "number";

const MAIN_DECK_SIZE = 50;
const colorLetters = { Yellow: "Y", Red: "R", Blue: "B", Green: "G", Pink: "P" };
const colorOrder = { Yellow: 0, Red: 1, Blue: 2, Green: 3, Pink: 4 };
const typeOrder = { Leader: 0, "Main Deck": 1, "JUMP Deck": 2 };

const elements = {
  databaseTab: document.querySelector("#databaseTab"),
  deckTab: document.querySelector("#deckTab"),
  deckTabCount: document.querySelector("#deckTabCount"),
  databaseView: document.querySelector("#databaseView"),
  deckView: document.querySelector("#deckView"),
  backToDatabase: document.querySelector("#backToDatabase"),
  clearDeck: document.querySelector("#clearDeck"),
  finalizeDeck: document.querySelector("#finalizeDeck"),
  exportTemplateSelect: document.querySelector("#exportTemplateSelect"),
  deckStatusPill: document.querySelector("#deckStatusPill"),
  playableOnlyToggle: document.querySelector("#playableOnlyToggle"),
  deckSortSelect: document.querySelector("#deckSortSelect"),
  searchInput: document.querySelector("#searchInput"),
  releaseFilters: document.querySelector("#releaseFilters"),
  setFilters: document.querySelector("#setFilters"),
  colorFilters: document.querySelector("#colorFilters"),
  typeFilters: document.querySelector("#typeFilters"),
  sortSelect: document.querySelector("#sortSelect"),
  resetButton: document.querySelector("#resetButton"),
  resultCount: document.querySelector("#resultCount"),
  cardGrid: document.querySelector("#cardGrid"),
  emptyState: document.querySelector("#emptyState"),
  themeToggle: document.querySelector("#themeToggle"),
  modal: document.querySelector("#cardModal"),
  modalImage: document.querySelector("#modalImage"),
  modalTitle: document.querySelector("#modalTitle"),
  modalMeta: document.querySelector("#modalMeta"),
  modalPrev: document.querySelector("#modalPrev"),
  modalNext: document.querySelector("#modalNext"),
  modalAddToDeck: document.querySelector("#modalAddToDeck"),
  modalAddFourToDeck: document.querySelector("#modalAddFourToDeck"),
  modalRemoveFromDeck: document.querySelector("#modalRemoveFromDeck"),
  modalDeckQty: document.querySelector("#modalDeckQty"),
  leaderStatus: document.querySelector("#leaderStatus"),
  leaderDeckList: document.querySelector("#leaderDeckList"),
  mainDeckCount: document.querySelector("#mainDeckCount"),
  jumpDeckCount: document.querySelector("#jumpDeckCount"),
  mainDeckList: document.querySelector("#mainDeckList"),
  jumpDeckList: document.querySelector("#jumpDeckList"),
  deckMessages: document.querySelector("#deckMessages"),
  toast: document.querySelector("#toast")
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  setupTheme();
  loadDeck();
  try {
    const response = await fetch("cards.json");
    if (!response.ok) throw new Error("Could not load cards.json");
    allCards = await response.json();
    allCards = allCards.map(normalizeCard);
    allCards = sortCards(allCards, "default");
    populateFilterButtons();
    addEventListeners();
    renderCards();
    renderDeck();
  } catch (error) {
    console.error(error);
    elements.resultCount.textContent = "Could not load cards.json.";
    elements.cardGrid.innerHTML = `<div class="empty-state"><h2>Could not load cards</h2><p>Use a local web server instead of opening index.html directly.</p></div>`;
  }
}

function normalizeCard(card) {
  const type = card.cardType || "Normal";
  const deckZone = card.deckZone || "Main";
  const deckLimit = Number(card.deckLimit || (type === "Leader" || type === "Secret Rare" || deckZone === "JUMP" ? 1 : 4));
  const deckCategory = type === "Leader" ? "Leader" : (deckZone === "JUMP" ? "JUMP Deck" : "Main Deck");
  return { ...card, cardType: type, deckZone, deckLimit, deckCategory };
}

function setupTheme() {
  const savedTheme = localStorage.getItem("sjtcg-theme");
  if (savedTheme === "dark") document.body.classList.add("dark");
  updateThemeButton();
  elements.themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("dark");
    localStorage.setItem("sjtcg-theme", document.body.classList.contains("dark") ? "dark" : "light");
    updateThemeButton();
  });
}
function updateThemeButton() { elements.themeToggle.textContent = document.body.classList.contains("dark") ? "Light" : "Dark"; }

function addEventListeners() {
  elements.databaseTab.addEventListener("click", () => showView("database"));
  elements.deckTab.addEventListener("click", () => showView("deck"));
  elements.backToDatabase.addEventListener("click", () => showView("database"));
  elements.clearDeck.addEventListener("click", clearDeck);
  elements.finalizeDeck.addEventListener("click", finalizeDeckImage);
  elements.searchInput.addEventListener("input", renderCards);
  elements.sortSelect.addEventListener("change", renderCards);
  elements.resetButton.addEventListener("click", resetFilters);
  if (elements.playableOnlyToggle) elements.playableOnlyToggle.addEventListener("change", renderCards);
  elements.deckSortSelect.addEventListener("change", () => { deckSortMode = elements.deckSortSelect.value; renderDeck(); });
  elements.modalPrev.addEventListener("click", () => showRelativeCard(-1));
  elements.modalNext.addEventListener("click", () => showRelativeCard(1));
  elements.modalAddToDeck.addEventListener("click", () => {
    const card = modalCards[currentModalIndex];
    if (card) addCardToDeck(card.number);
  });
  elements.modalAddFourToDeck.addEventListener("click", () => {
    const card = modalCards[currentModalIndex];
    if (card) addCardCopiesToDeck(card.number, 4);
  });
  elements.modalRemoveFromDeck.addEventListener("click", () => {
    const card = modalCards[currentModalIndex];
    if (card) removeCardFromDeckByCard(card);
  });
  document.querySelectorAll("[data-close-modal]").forEach((element) => element.addEventListener("click", closeModal));
  document.addEventListener("keydown", (event) => {
    if (elements.modal.hidden) return;
    if (event.key === "Escape") closeModal();
    if (event.key === "ArrowLeft") showRelativeCard(-1);
    if (event.key === "ArrowRight") showRelativeCard(1);
  });
}

function showView(view) {
  const deckShown = view === "deck";
  elements.databaseView.hidden = deckShown;
  elements.deckView.hidden = !deckShown;
  elements.databaseTab.classList.toggle("active", !deckShown);
  elements.deckTab.classList.toggle("active", deckShown);
  if (deckShown) renderDeck();
}

function populateFilterButtons() {
  renderFilterGroup(elements.releaseFilters, uniqueValues(allCards.map(c => c.release)).sort(compareRelease), "release");
  renderFilterGroup(elements.setFilters, uniqueValues(allCards.map(c => c.set)).sort(compareText), "set");
  renderFilterGroup(elements.colorFilters, uniqueValues(allCards.map(c => c.color)).sort(compareColors), "color");
  renderFilterGroup(elements.typeFilters, uniqueValues(allCards.map(c => c.deckCategory)).sort(compareTypes), "type");
}
function renderFilterGroup(container, values, type) { container.innerHTML = ""; values.forEach(value => container.appendChild(makeFilterButton(value, type))); }
function makeFilterButton(value, type) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `filter-button ${type === "color" ? "color-button" : ""}`;
  button.dataset.filterType = type;
  button.dataset.filterValue = value;
  if (type === "color") { button.innerHTML = colorBadgeHtml(value); button.title = value; button.setAttribute("aria-label", `${value} cards`); }
  else { button.textContent = value; }
  button.addEventListener("click", () => { activeFilters[type] = activeFilters[type] === value ? "" : value; renderCards(); });
  return button;
}
function updateFilterButtons() {
  document.querySelectorAll(".filter-button").forEach(button => {
    const type = button.dataset.filterType, value = button.dataset.filterValue;
    button.classList.toggle("active", activeFilters[type] === value);
    button.setAttribute("aria-pressed", activeFilters[type] === value ? "true" : "false");
  });
}
function uniqueValues(values) { return [...new Set(values.filter(Boolean))]; }

function renderCards() {
  const searchText = elements.searchInput.value.trim().toLowerCase();
  const leader = selectedLeader();
  const playableOnly = Boolean(elements.playableOnlyToggle && elements.playableOnlyToggle.checked && leader);
  visibleCards = allCards.filter(card => {
    const searchableText = [card.number, card.release, card.set, card.color, card.cardType, card.deckZone, card.deckCategory, card.rarity].join(" ").toLowerCase();
    const isPlayableWithLeader = !playableOnly || card.number === leader.number || card.color === leader.color;
    return isPlayableWithLeader &&
      (!searchText || searchableText.includes(searchText)) &&
      (!activeFilters.release || card.release === activeFilters.release) &&
      (!activeFilters.set || card.set === activeFilters.set) &&
      (!activeFilters.color || card.color === activeFilters.color) &&
      (!activeFilters.type || card.deckCategory === activeFilters.type);
  });
  visibleCards = sortCards(visibleCards, elements.sortSelect.value);
  elements.cardGrid.innerHTML = "";
  visibleCards.forEach((card, index) => elements.cardGrid.appendChild(createCardElement(card, index)));
  elements.resultCount.textContent = `${visibleCards.length} card${visibleCards.length === 1 ? "" : "s"} found`;
  elements.emptyState.hidden = visibleCards.length !== 0;
  updateFilterButtons();
}

function sortCards(cards, sortBy) {
  return [...cards].sort((a, b) => {
    if (sortBy === "release") return compareRelease(a.release, b.release) || compareCardNumbers(a.number, b.number);
    if (sortBy === "set") return compareText(a.set, b.set) || compareRelease(a.release, b.release) || compareCardNumbers(a.number, b.number);
    if (sortBy === "color") return compareColors(a.color, b.color) || compareDefault(a, b);
    if (sortBy === "type") return compareTypes(a.deckCategory, b.deckCategory) || compareDefault(a, b);
    if (sortBy === "number") return compareCardNumbers(a.number, b.number);
    return compareDefault(a, b);
  });
}
function compareDefault(a, b) { return compareRelease(a.release, b.release) || compareCardNumbers(a.number, b.number); }
function compareRelease(a, b) {
  const order = { ST: 0, SD: 1, EX: 2, PUP: 99 };
  const pa = parseRelease(a), pb = parseRelease(b);
  return (order[pa.family] ?? 50) - (order[pb.family] ?? 50) || pa.family.localeCompare(pb.family) || pa.number - pb.number;
}
function parseRelease(value) { const match = String(value || "").match(/^([A-Z]+)(\d*)$/); return { family: match ? match[1] : String(value || ""), number: match && match[2] ? Number(match[2]) : 0 }; }
function compareText(a, b) { return String(a || "").localeCompare(String(b || "")); }
function compareColors(a, b) { return (colorOrder[a] ?? 99) - (colorOrder[b] ?? 99) || compareText(a, b); }
function compareTypes(a, b) { return (typeOrder[a] ?? 99) - (typeOrder[b] ?? 99) || compareText(a, b); }
function compareCardNumbers(a, b) { return String(a || "").localeCompare(String(b || ""), undefined, { numeric: true, sensitivity: "base" }); }

function createCardElement(card, index) {
  const article = document.createElement("article");
  const deckQty = totalCopiesInDeck(card.number);
  article.className = `card ${deckQty ? "in-deck" : ""}`;
  article.dataset.cardNumber = card.number;
  article.tabIndex = 0;
  article.setAttribute("role", "button");
  article.setAttribute("aria-label", `Open ${card.number}`);
  article.innerHTML = `<div class="card-image-wrap"><img src="${escapeHtml(card.image)}" alt="${escapeHtml(card.number)}" loading="lazy" decoding="async"><strong class="database-deck-qty" ${deckQty ? "" : "hidden"}>×${deckQty}</strong></div><div><h2>${escapeHtml(card.number)}</h2><p>Release: ${escapeHtml(card.release)} · Set: ${escapeHtml(card.set)}</p><p class="card-color-line">${colorBadgeHtml(card.color)}</p><p class="card-meta-line">${cardBadgesHtml(card)}</p><div class="card-actions"><button class="add-button" type="button" aria-label="Add ${escapeHtml(card.number)} to deck">+</button></div></div>`;
  const image = article.querySelector("img");
  image.addEventListener("error", () => { image.src = createPlaceholderImage(card.number); });
  article.addEventListener("click", () => openModal(visibleCards, index));
  article.querySelector(".add-button").addEventListener("click", (event) => { event.stopPropagation(); addCardToDeck(card.number); });
  article.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openModal(visibleCards, index); } });
  return article;
}

function cardBadgesHtml(card) {
  const badges = [];
  if (card.cardType === "Leader") badges.push(`<span class="badge leader">Leader</span>`);
  if (card.cardType === "Secret Rare") badges.push(`<span class="badge secret">Secret Rare</span>`);
  if (card.deckZone === "JUMP") badges.push(`<span class="badge jump">JUMP Deck</span>`);
  if (!badges.length) badges.push(`<span class="badge">Limit ${card.deckLimit}</span>`);
  else badges.push(`<span class="badge">Limit ${card.deckLimit}</span>`);
  return badges.join(" ");
}
function colorBadgeHtml(color) { const safeColor = escapeHtml(color || "Unknown"); const letter = escapeHtml(colorLetters[color] || "?"); return `<span class="color-badge color-${safeColor.toLowerCase()}" title="${safeColor}">${letter}</span>`; }

function openModal(cards, index) { modalCards = cards || visibleCards; currentModalIndex = index; showModalCard(); elements.modal.hidden = false; document.body.style.overflow = "hidden"; }
function showModalCard() {
  const card = modalCards[currentModalIndex];
  if (!card) return;
  elements.modalImage.onerror = () => { elements.modalImage.src = createPlaceholderImage(card.number); };
  elements.modalImage.src = card.image;
  elements.modalImage.alt = card.number;
  elements.modalTitle.textContent = card.number;
  elements.modalMeta.innerHTML = `<span><strong>Release:</strong> ${escapeHtml(card.release)}</span><span><strong>Set:</strong> ${escapeHtml(card.set)}</span><span><strong>Color:</strong> ${colorBadgeHtml(card.color)}</span><span><strong>Type:</strong> ${escapeHtml(card.deckCategory)}</span><span><strong>Limit:</strong> ${card.deckLimit}</span><span>${cardBadgesHtml(card)}</span>`;
  updateModalDeckControls(card);
}
function showRelativeCard(offset) { if (!modalCards.length) return; currentModalIndex = (currentModalIndex + offset + modalCards.length) % modalCards.length; showModalCard(); }
function closeModal() { elements.modal.hidden = true; document.body.style.overflow = ""; }
function resetFilters() { elements.searchInput.value = ""; elements.sortSelect.value = "default"; activeFilters = { release: "", set: "", color: "", type: "" }; renderCards(); }

function getCard(number) { return allCards.find(card => card.number === number); }
function loadDeck() { try { deck = JSON.parse(localStorage.getItem("sjtcg-deck") || "") || deck; } catch { deck = { leader: "", main: {}, jump: {} }; } deck.main ||= {}; deck.jump ||= {}; deck.leader ||= ""; }
function saveDeck() {
  localStorage.setItem("sjtcg-deck", JSON.stringify(deck));
  renderDeck();
  updateDatabaseDeckBadges();
  if (elements.playableOnlyToggle && elements.playableOnlyToggle.checked) renderCards();
}
function totalCopiesInDeck(number) {
  return Number(deck.main[number] || 0) + Number(deck.jump[number] || 0);
}
function updateDatabaseDeckBadges() {
  document.querySelectorAll(".card").forEach(cardElement => {
    const number = cardElement.dataset.cardNumber;
    const badge = cardElement.querySelector(".database-deck-qty");
    const qty = totalCopiesInDeck(number);
    if (!badge) return;
    badge.textContent = qty ? `×${qty}` : "";
    badge.hidden = qty <= 0;
    cardElement.classList.toggle("in-deck", qty > 0);
  });
}
function mainDeckTotal() { return Object.values(deck.main).reduce((sum, qty) => sum + Number(qty || 0), 0); }
function jumpDeckTotal() { return Object.values(deck.jump).reduce((sum, qty) => sum + Number(qty || 0), 0); }
function selectedLeader() { return deck.leader ? getCard(deck.leader) : null; }

function addCardToDeck(number, options = {}) {
  const quiet = Boolean(options.quiet);
  const card = getCard(number);
  if (!card) return;
  const leader = selectedLeader();
  if (card.cardType === "Leader") {
    deck.leader = card.number;
    deck.main = { ...deck.main, [card.number]: 1 };
    // Remove other leaders from main deck.
    Object.keys(deck.main).forEach(n => { const c = getCard(n); if (c && c.cardType === "Leader" && n !== card.number) delete deck.main[n]; });
    if (!quiet) showToast(`${card.number} selected as your Leader.`);
    saveDeck();
    return;
  }
  if (!leader) { if (!quiet) showToast("Choose a Leader first."); return; }
  if (card.color !== leader.color) { if (!quiet) showToast(`This card is ${card.color}. Your Leader is ${leader.color}.`); return; }
  const zone = card.deckZone === "JUMP" ? "jump" : "main";
  const currentQty = Number(deck[zone][card.number] || 0);
  if (currentQty >= card.deckLimit) { if (!quiet) showToast(`${card.number} is limited to ${card.deckLimit}.`); return; }
  if (zone === "main" && mainDeckTotal() >= MAIN_DECK_SIZE) { if (!quiet) showToast("Main Deck is already at 50 cards."); return; }
  deck[zone][card.number] = currentQty + 1;
  if (!quiet) showToast(`${card.number} added to ${zone === "jump" ? "JUMP Deck" : "Main Deck"}.`);
  saveDeck();
}
function removeOne(number, zone) {
  if (!deck[zone][number]) return;
  deck[zone][number] -= 1;
  if (deck[zone][number] <= 0) delete deck[zone][number];
  if (number === deck.leader) deck.leader = "";
  saveDeck();
}
function addOne(number, zone) { addCardToDeck(number); }
function addCardCopiesToDeck(number, requestedCopies) {
  const card = getCard(number);
  if (!card) return;
  let added = 0;
  for (let i = 0; i < requestedCopies; i++) {
    const before = getDeckQuantity(card);
    addCardToDeck(number, { quiet: true });
    const after = getDeckQuantity(card);
    if (after <= before) break;
    added++;
  }
  if (added) showToast(`${card.number}: added ${added}.`);
  else showToast(`Could not add more copies of ${card.number}.`);
  renderDeck();
  updateModalDeckControls(card);
}
function clearDeck() {
  if (!confirm("Clear your saved deck? This removes the Leader, Main Deck, and JUMP Deck from this browser.")) return;
  deck = { leader: "", main: {}, jump: {} };
  saveDeck();
  showToast("Deck cleared.");
}

function renderDeck() {
  const leader = selectedLeader();
  const mainTotal = mainDeckTotal(), jumpTotal = jumpDeckTotal();
  elements.deckTabCount.textContent = `${mainTotal}/${MAIN_DECK_SIZE}`;
  elements.leaderStatus.innerHTML = leader ? `${escapeHtml(leader.number)} ${colorBadgeHtml(leader.color)}` : "None selected";
  elements.mainDeckCount.textContent = `${mainTotal} / ${MAIN_DECK_SIZE}`;
  elements.jumpDeckCount.textContent = `${jumpTotal}`;
  if (elements.playableOnlyToggle) {
    elements.playableOnlyToggle.disabled = !leader;
    elements.playableOnlyToggle.closest("label")?.classList.toggle("disabled", !leader);
  }
  renderLeaderDeckPanel(leader);
  renderDeckList(elements.mainDeckList, deck.main, "main");
  renderDeckList(elements.jumpDeckList, deck.jump, "jump");
  renderDeckStatusPill(leader, mainTotal);
  renderDeckMessages(leader, mainTotal);
}
function getDeckRows(entries) {
  return Object.entries(entries)
    .map(([number, qty]) => ({ card: getCard(number), qty: Number(qty || 0) }))
    .filter(row => row.card)
    .sort(compareDeckRows);
}
function compareDeckRows(a, b) {
  if (deckSortMode === "quantity") return b.qty - a.qty || compareDefault(a.card, b.card);
  if (deckSortMode === "color") return compareColors(a.card.color, b.card.color) || compareDefault(a.card, b.card);
  if (deckSortMode === "set") return compareText(a.card.set, b.card.set) || compareDefault(a.card, b.card);
  if (deckSortMode === "type") return compareTypes(a.card.deckCategory, b.card.deckCategory) || compareDefault(a.card, b.card);
  return compareDefault(a.card, b.card);
}
function renderLeaderDeckPanel(leader) {
  if (!elements.leaderDeckList) return;
  if (!leader) { elements.leaderDeckList.innerHTML = `<p class="deck-message">No Leader selected.</p>`; return; }
  elements.leaderDeckList.innerHTML = "";
  const tile = document.createElement("article");
  tile.className = "deck-card-tile leader-tile";
  tile.tabIndex = 0;
  tile.setAttribute("role", "button");
  tile.setAttribute("aria-label", `Open ${leader.number} in deck viewer`);
  tile.innerHTML = `<div class="deck-card-image-wrap"><img src="${escapeHtml(leader.image)}" alt="${escapeHtml(leader.number)}" loading="lazy" decoding="async"><strong class="deck-card-qty">×1</strong></div><div class="deck-card-caption"><strong>${escapeHtml(leader.number)}</strong><span>${colorBadgeHtml(leader.color)} ${escapeHtml(leader.set)}</span><small>Leader · Limit ${leader.deckLimit}</small></div><div class="qty-controls deck-tile-controls"><button type="button" aria-label="Remove ${escapeHtml(leader.number)} as Leader">−</button></div>`;
  tile.querySelector("button").addEventListener("click", (event) => { event.stopPropagation(); removeOne(leader.number, "main"); });
  tile.addEventListener("click", () => openModal([leader], 0));
  tile.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openModal([leader], 0); } });
  elements.leaderDeckList.appendChild(tile);
}

function renderDeckList(container, entries, zone) {
  let rows = getDeckRows(entries);
  if (zone === "main") rows = rows.filter(({card}) => card.cardType !== "Leader");
  if (!rows.length) { container.innerHTML = `<p class="deck-message">No cards yet.</p>`; return; }
  const cardsInThisZone = rows.map(row => row.card);
  container.innerHTML = "";
  rows.forEach(({card, qty}, index) => {
    const tile = document.createElement("article");
    tile.className = "deck-card-tile";
    tile.tabIndex = 0;
    tile.setAttribute("role", "button");
    tile.setAttribute("aria-label", `Open ${card.number} in deck viewer`);
    tile.innerHTML = `<div class="deck-card-image-wrap"><img src="${escapeHtml(card.image)}" alt="${escapeHtml(card.number)}" loading="lazy" decoding="async"><strong class="deck-card-qty">×${qty}</strong></div><div class="deck-card-caption"><strong>${escapeHtml(card.number)}</strong><span>${colorBadgeHtml(card.color)} ${escapeHtml(card.set)}</span><small>${escapeHtml(card.deckCategory)} · Limit ${card.deckLimit}</small></div><div class="qty-controls deck-tile-controls"><button type="button" aria-label="Remove one ${escapeHtml(card.number)}">−</button><button type="button" aria-label="Add one ${escapeHtml(card.number)}">+</button></div>`;
    tile.querySelectorAll("button")[0].addEventListener("click", (event) => { event.stopPropagation(); removeOne(card.number, zone); });
    tile.querySelectorAll("button")[1].addEventListener("click", (event) => { event.stopPropagation(); addOne(card.number, zone); });
    tile.addEventListener("click", () => openModal(cardsInThisZone, index));
    tile.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openModal(cardsInThisZone, index); } });
    container.appendChild(tile);
  });
}

function cardDeckZoneKey(card) { return card.deckZone === "JUMP" ? "jump" : "main"; }
function getDeckQuantity(card) {
  if (!card) return 0;
  const zone = cardDeckZoneKey(card);
  return Number(deck[zone][card.number] || 0);
}
function updateModalDeckControls(card) {
  const zoneName = card.deckZone === "JUMP" ? "JUMP Deck" : "Main Deck";
  const qty = getDeckQuantity(card);
  const remaining = Math.max(0, card.deckLimit - qty);
  elements.modalAddToDeck.textContent = `+`;
  elements.modalDeckQty.textContent = `${qty} in ${zoneName}`;
  elements.modalRemoveFromDeck.disabled = qty <= 0;
  elements.modalAddToDeck.disabled = remaining <= 0 || (card.deckZone !== "JUMP" && card.cardType !== "Leader" && mainDeckTotal() >= MAIN_DECK_SIZE);
  elements.modalAddFourToDeck.hidden = card.deckLimit <= 1 || card.deckZone === "JUMP" || card.cardType === "Leader";
  elements.modalAddFourToDeck.disabled = remaining <= 0 || mainDeckTotal() >= MAIN_DECK_SIZE;
}
function removeCardFromDeckByCard(card) {
  const zone = cardDeckZoneKey(card);
  removeOne(card.number, zone);
  updateModalDeckControls(card);
}

async function finalizeDeckImage() {
  const leader = selectedLeader();
  const mainRows = getDeckRows(deck.main).filter(({card}) => card.cardType !== "Leader");
  const jumpRows = getDeckRows(deck.jump);
  if (!leader) { showToast("Choose a Leader before finalizing."); return; }
  if (mainDeckTotal() !== MAIN_DECK_SIZE) { showToast("Main Deck must be exactly 50 cards before finalizing."); return; }
  try {
    showToast("Building deck image...");
    const fileName = await buildDeckCanvasDownload(leader, mainRows, jumpRows, elements.exportTemplateSelect.value);
    showToast(`${fileName} downloaded.`);
  } catch (error) {
    console.error(error);
    showToast("Could not create the deck image.");
  }
}
function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}
async function buildDeckCanvasDownload(leader, mainRows, jumpRows, template = "large") {
  const templates = {
    compact: { cardW: 180, cols: 10, gap: 18, label: "compact" },
    large: { cardW: 320, cols: 6, gap: 28, label: "large" },
    social: { cardW: 300, cols: 5, gap: 26, label: "social" }
  };
  const selected = templates[template] || templates.large;
  const cardW = selected.cardW;
  const cardH = Math.round(cardW * 1.4);
  const gap = selected.gap;
  const cols = selected.cols;
  const headerH = 170;
  const sectionTitleH = 56;
  const footerH = 44;
  const width = cols * cardW + (cols + 1) * gap;

  const jumpCardW = Math.min(Math.round(cardW * 1.65), Math.floor((width - gap * 2) / 2));
  const jumpCardH = Math.round(jumpCardW * 0.75);
  const jumpCols = Math.max(1, Math.floor((width - gap) / (jumpCardW + gap)));

  const mainRowsCount = Math.ceil(mainRows.length / cols) || 1;
  const jumpRowsCount = Math.ceil(jumpRows.length / jumpCols) || 0;
  const leaderRowsCount = 1;
  const height = headerH + sectionTitleH + leaderRowsCount * (cardH + gap) + sectionTitleH + mainRowsCount * (cardH + gap) +
    (jumpRows.length ? sectionTitleH + jumpRowsCount * (jumpCardH + gap) : 0) + footerH;

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = document.body.classList.contains("dark") ? "#0d0d0f" : "#f4f1e8";
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = document.body.classList.contains("dark") ? "#f6efe2" : "#151515";
  ctx.font = "900 58px Arial, sans-serif";
  ctx.fillText("SJTCG Deck List", gap, 72);
  ctx.font = "700 30px Arial, sans-serif";
  drawExportHeaderLine(ctx, leader, gap, 122);

  let y = headerH;
  y = await drawDeckSection(ctx, "Leader", [{ card: leader, qty: 1 }], y, { cardW, cardH, gap, cols, fit: "cover" });
  y = await drawDeckSection(ctx, "Main Deck", mainRows, y, { cardW, cardH, gap, cols, fit: "cover" });
  if (jumpRows.length) {
    y = await drawDeckSection(ctx, "JUMP Deck", jumpRows, y, { cardW: jumpCardW, cardH: jumpCardH, gap, cols: jumpCols, fit: "contain" });
  }

  ctx.fillStyle = document.body.classList.contains("dark") ? "#c8b98f" : "#6d6251";
  ctx.font = "700 16px Arial, sans-serif";
  ctx.fillText("Generated locally from SJTCG Card Database", gap, height - 12);
  const link = document.createElement("a");
  const fileName = `SJTCG-deck-${leader.number}-${(template || "large")}.png`;
  link.download = fileName;
  link.href = canvas.toDataURL("image/png");
  link.click();
  return fileName;
}
function drawExportHeaderLine(ctx, leader, x, y) {
  ctx.font = "700 30px Arial, sans-serif";
  ctx.fillStyle = document.body.classList.contains("dark") ? "#f6efe2" : "#151515";
  const before = `Leader: ${leader.number}  •  `;
  ctx.fillText(before, x, y);
  let cursor = x + ctx.measureText(before).width + 16;
  const badgeSize = 34;
  drawColorBadgeOnCanvas(ctx, leader.color, cursor, y - 26, badgeSize);
  cursor += badgeSize + 22;
  ctx.fillText(`•  Main: ${mainDeckTotal()}/50  •  JUMP: ${jumpDeckTotal()}`, cursor, y);
}
function drawColorBadgeOnCanvas(ctx, color, x, y, size) {
  const fills = { Yellow: "#ffd84d", Red: "#ef5350", Blue: "#42a5f5", Green: "#66bb6a", Pink: "#f48fb1" };
  const textColors = { Yellow: "#111", Red: "#fff", Blue: "#fff", Green: "#fff", Pink: "#111" };
  ctx.save();
  ctx.beginPath();
  ctx.arc(x + size / 2, y + size / 2, size / 2, 0, Math.PI * 2);
  ctx.fillStyle = fills[color] || "#ddd";
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = "rgba(0,0,0,0.25)";
  ctx.stroke();
  ctx.fillStyle = textColors[color] || "#111";
  ctx.font = "900 19px Arial, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(colorLetters[color] || "?", x + size / 2, y + size / 2 + 1);
  ctx.restore();
}

async function drawDeckSection(ctx, title, rows, y, layout) {
  const { cardW, cardH, gap, cols, fit = "cover" } = layout;
  ctx.fillStyle = document.body.classList.contains("dark") ? "#f6efe2" : "#151515";
  ctx.font = "900 38px Arial, sans-serif";
  ctx.fillText(title, gap, y + 38);
  y += 56;
  for (let i = 0; i < rows.length; i++) {
    const { card, qty } = rows[i];
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = gap + col * (cardW + gap);
    const cy = y + row * (cardH + gap);
    try {
      const img = await loadImage(card.image);
      if (fit === "contain") {
        ctx.fillStyle = document.body.classList.contains("dark") ? "#171717" : "#fffaf0";
        ctx.fillRect(x, cy, cardW, cardH);
        drawImageContain(ctx, img, x, cy, cardW, cardH);
      } else {
        drawImageCover(ctx, img, x, cy, cardW, cardH);
      }
    } catch {
      ctx.fillStyle = "#222"; ctx.fillRect(x, cy, cardW, cardH);
    }
    drawQuantityBadge(ctx, qty, x, cy, cardW, cardH);
  }
  return y + (Math.ceil(rows.length / cols) || 1) * (cardH + gap);
}
function drawImageCover(ctx, img, x, y, w, h) {
  const scale = Math.max(w / img.naturalWidth, h / img.naturalHeight);
  const sw = w / scale;
  const sh = h / scale;
  const sx = (img.naturalWidth - sw) / 2;
  const sy = (img.naturalHeight - sh) / 2;
  ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h);
}
function drawImageContain(ctx, img, x, y, w, h) {
  const scale = Math.min(w / img.naturalWidth, h / img.naturalHeight);
  const dw = img.naturalWidth * scale;
  const dh = img.naturalHeight * scale;
  const dx = x + (w - dw) / 2;
  const dy = y + (h - dh) / 2;
  ctx.drawImage(img, dx, dy, dw, dh);
}
function drawQuantityBadge(ctx, qty, x, y, w, h) {
  const badgeW = Math.max(34, Math.round(w * 0.16));
  const badgeH = Math.max(24, Math.round(badgeW * 0.58));
  const pad = Math.max(5, Math.round(w * 0.025));
  const bx = x + w - badgeW - pad;
  const by = y + h - badgeH - pad;
  ctx.fillStyle = "rgba(0,0,0,0.72)";
  ctx.beginPath();
  ctx.roundRect(bx, by, badgeW, badgeH, Math.round(badgeH / 2));
  ctx.fill();
  ctx.fillStyle = "#fff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `900 ${Math.max(16, Math.round(badgeH * 0.58))}px Arial, sans-serif`;
  ctx.fillText(`×${qty}`, bx + badgeW / 2, by + badgeH / 2 + 1);
  ctx.textAlign = "start";
  ctx.textBaseline = "alphabetic";
}

function renderDeckStatusPill(leader, mainTotal) {
  if (!elements.deckStatusPill) return;
  const limitProblems = findLimitProblems().length;
  const colorProblems = findColorProblems(leader).length;
  const isLegal = Boolean(leader) && mainTotal === MAIN_DECK_SIZE && !limitProblems && !colorProblems;
  const leaderText = leader ? `${escapeHtml(leader.number)} ${colorBadgeHtml(leader.color)}` : "No Leader";
  const statusText = isLegal ? "Legal" : "Needs work";
  elements.deckStatusPill.classList.toggle("legal", isLegal);
  elements.deckStatusPill.classList.toggle("needs-work", !isLegal);
  elements.deckStatusPill.innerHTML = `<strong>${statusText}</strong><span>Leader: ${leaderText}</span><span>Main Deck: ${mainTotal}/${MAIN_DECK_SIZE}</span><span>JUMP: ${jumpDeckTotal()}</span>`;
}

function renderDeckMessages(leader, mainTotal) {
  const invalidLimits = findLimitProblems();
  const colorProblems = findColorProblems(leader);
  const checks = [
    [leader ? "good" : "warn", leader ? `Leader selected: ${escapeHtml(leader.number)} ${colorBadgeHtml(leader.color)}` : "Choose one Leader"],
    [mainTotal === MAIN_DECK_SIZE ? "good" : "warn", mainTotal === MAIN_DECK_SIZE ? "Main Deck is 50 / 50" : `Main Deck is ${mainTotal} / 50`],
    [colorProblems.length ? "error" : "good", colorProblems.length ? `${colorProblems.length} card color issue${colorProblems.length === 1 ? "" : "s"}` : "Color restriction is valid"],
    [invalidLimits.length ? "error" : "good", invalidLimits.length ? `${invalidLimits.length} card limit issue${invalidLimits.length === 1 ? "" : "s"}` : "Card copy limits are valid"],
    ["good", `JUMP Deck: ${jumpDeckTotal()} card${jumpDeckTotal() === 1 ? "" : "s"}`]
  ];
  elements.deckMessages.innerHTML = checks.map(([kind, html]) => `<div class="deck-message ${kind}"><span class="check-icon">${kind === "good" ? "✓" : kind === "error" ? "!" : "•"}</span><span>${html}</span></div>`).join("");
}
function findLimitProblems() {
  const rows = [...getDeckRows(deck.main), ...getDeckRows(deck.jump)];
  return rows.filter(({card, qty}) => qty > card.deckLimit);
}
function findColorProblems(leader) {
  if (!leader) return [];
  const rows = [...getDeckRows(deck.main), ...getDeckRows(deck.jump)];
  return rows.filter(({card}) => card.cardType !== "Leader" && card.color !== leader.color);
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { elements.toast.hidden = true; }, 2200);
}

function escapeHtml(value) { return String(value || "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
function createPlaceholderImage(cardNumber) { const safeNumber = escapeHtml(cardNumber || "Missing Image"); const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="500" height="700" viewBox="0 0 500 700"><rect width="500" height="700" rx="32" fill="#171717"/><rect x="30" y="30" width="440" height="640" rx="24" fill="#231f17" stroke="#c89a2c" stroke-width="8"/><text x="250" y="320" text-anchor="middle" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#d2a642">Image missing</text><text x="250" y="370" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" fill="#f6efe2">${safeNumber}</text></svg>`; return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`; }
