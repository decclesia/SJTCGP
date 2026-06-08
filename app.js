// SJTCG static card image database + local deckbuilder
let allCards = [];
let visibleCards = [];
let currentModalIndex = -1;
let activeFilters = { release: "", set: "", color: "", type: "" };
let deck = { leader: "", main: {}, jump: {} };

const MAIN_DECK_SIZE = 50;
const colorLetters = { Yellow: "Y", Red: "R", Blue: "B", Green: "G", Pink: "P" };
const colorOrder = { Yellow: 0, Red: 1, Blue: 2, Green: 3, Pink: 4 };
const typeOrder = { Leader: 0, "Secret Rare": 1, JUMP: 2, Normal: 3 };

const elements = {
  databaseTab: document.querySelector("#databaseTab"),
  deckTab: document.querySelector("#deckTab"),
  deckTabCount: document.querySelector("#deckTabCount"),
  databaseView: document.querySelector("#databaseView"),
  deckView: document.querySelector("#deckView"),
  backToDatabase: document.querySelector("#backToDatabase"),
  clearDeck: document.querySelector("#clearDeck"),
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
  leaderStatus: document.querySelector("#leaderStatus"),
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
  return { ...card, cardType: type, deckZone: card.deckZone || "Main", deckLimit: Number(card.deckLimit || (type === "Leader" || type === "Secret Rare" ? 1 : 4)) };
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
  elements.searchInput.addEventListener("input", renderCards);
  elements.sortSelect.addEventListener("change", renderCards);
  elements.resetButton.addEventListener("click", resetFilters);
  elements.modalPrev.addEventListener("click", () => showRelativeCard(-1));
  elements.modalNext.addEventListener("click", () => showRelativeCard(1));
  elements.modalAddToDeck.addEventListener("click", () => {
    const card = visibleCards[currentModalIndex];
    if (card) addCardToDeck(card.number);
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
  renderFilterGroup(elements.typeFilters, uniqueValues(allCards.map(c => c.cardType)).sort(compareTypes), "type");
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
  visibleCards = allCards.filter(card => {
    const searchableText = [card.number, card.release, card.set, card.color, card.cardType, card.deckZone].join(" ").toLowerCase();
    return (!searchText || searchableText.includes(searchText)) &&
      (!activeFilters.release || card.release === activeFilters.release) &&
      (!activeFilters.set || card.set === activeFilters.set) &&
      (!activeFilters.color || card.color === activeFilters.color) &&
      (!activeFilters.type || card.cardType === activeFilters.type);
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
    if (sortBy === "type") return compareTypes(a.cardType, b.cardType) || compareDefault(a, b);
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
  article.className = "card";
  article.tabIndex = 0;
  article.setAttribute("role", "button");
  article.setAttribute("aria-label", `Open ${card.number}`);
  article.innerHTML = `<img src="${escapeHtml(card.image)}" alt="${escapeHtml(card.number)}" loading="lazy"><div><h2>${escapeHtml(card.number)}</h2><p>Release: ${escapeHtml(card.release)} · Set: ${escapeHtml(card.set)}</p><p class="card-color-line">${colorBadgeHtml(card.color)} <span>${escapeHtml(card.color)}</span></p><p class="card-meta-line">${cardBadgesHtml(card)}</p><div class="card-actions"><button class="add-button" type="button">Add to ${card.deckZone === "JUMP" ? "JUMP" : "Deck"}</button></div></div>`;
  const image = article.querySelector("img");
  image.addEventListener("error", () => { image.src = createPlaceholderImage(card.number); });
  article.addEventListener("click", () => openModal(index));
  article.querySelector(".add-button").addEventListener("click", (event) => { event.stopPropagation(); addCardToDeck(card.number); });
  article.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openModal(index); } });
  return article;
}
function cardBadgesHtml(card) {
  const badges = [];
  if (card.cardType === "Leader") badges.push(`<span class="badge leader">Leader</span>`);
  if (card.cardType === "Secret Rare") badges.push(`<span class="badge secret">Secret Rare</span>`);
  if (card.deckZone === "JUMP") badges.push(`<span class="badge jump">JUMP</span>`);
  if (!badges.length) badges.push(`<span class="badge">Limit ${card.deckLimit}</span>`);
  else badges.push(`<span class="badge">Limit ${card.deckLimit}</span>`);
  return badges.join(" ");
}
function colorBadgeHtml(color) { const safeColor = escapeHtml(color || "Unknown"); const letter = escapeHtml(colorLetters[color] || "?"); return `<span class="color-badge color-${safeColor.toLowerCase()}" title="${safeColor}">${letter}</span>`; }

function openModal(index) { currentModalIndex = index; showModalCard(); elements.modal.hidden = false; document.body.style.overflow = "hidden"; }
function showModalCard() {
  const card = visibleCards[currentModalIndex];
  if (!card) return;
  elements.modalImage.onerror = () => { elements.modalImage.src = createPlaceholderImage(card.number); };
  elements.modalImage.src = card.image;
  elements.modalImage.alt = card.number;
  elements.modalTitle.textContent = card.number;
  elements.modalMeta.innerHTML = `Release: ${escapeHtml(card.release)} · Set: ${escapeHtml(card.set)} · Color: ${colorBadgeHtml(card.color)} ${escapeHtml(card.color)} · ${cardBadgesHtml(card)}`;
  elements.modalAddToDeck.textContent = `Add to ${card.deckZone === "JUMP" ? "JUMP Deck" : "Deck"}`;
}
function showRelativeCard(offset) { if (!visibleCards.length) return; currentModalIndex = (currentModalIndex + offset + visibleCards.length) % visibleCards.length; showModalCard(); }
function closeModal() { elements.modal.hidden = true; document.body.style.overflow = ""; }
function resetFilters() { elements.searchInput.value = ""; elements.sortSelect.value = "default"; activeFilters = { release: "", set: "", color: "", type: "" }; renderCards(); }

function getCard(number) { return allCards.find(card => card.number === number); }
function loadDeck() { try { deck = JSON.parse(localStorage.getItem("sjtcg-deck") || "") || deck; } catch { deck = { leader: "", main: {}, jump: {} }; } deck.main ||= {}; deck.jump ||= {}; deck.leader ||= ""; }
function saveDeck() { localStorage.setItem("sjtcg-deck", JSON.stringify(deck)); renderDeck(); }
function mainDeckTotal() { return Object.values(deck.main).reduce((sum, qty) => sum + Number(qty || 0), 0); }
function jumpDeckTotal() { return Object.values(deck.jump).reduce((sum, qty) => sum + Number(qty || 0), 0); }
function selectedLeader() { return deck.leader ? getCard(deck.leader) : null; }

function addCardToDeck(number) {
  const card = getCard(number);
  if (!card) return;
  const leader = selectedLeader();
  if (card.cardType === "Leader") {
    deck.leader = card.number;
    deck.main = { ...deck.main, [card.number]: 1 };
    // Remove other leaders from main deck.
    Object.keys(deck.main).forEach(n => { const c = getCard(n); if (c && c.cardType === "Leader" && n !== card.number) delete deck.main[n]; });
    showToast(`${card.number} selected as your Leader.`);
    saveDeck();
    return;
  }
  if (!leader) { showToast("Choose a Leader first."); return; }
  if (card.color !== leader.color) { showToast(`This card is ${card.color}. Your Leader is ${leader.color}.`); return; }
  const zone = card.deckZone === "JUMP" ? "jump" : "main";
  const currentQty = Number(deck[zone][card.number] || 0);
  if (currentQty >= card.deckLimit) { showToast(`${card.number} is limited to ${card.deckLimit}.`); return; }
  if (zone === "main" && mainDeckTotal() >= MAIN_DECK_SIZE) { showToast("Main Deck is already at 50 cards."); return; }
  deck[zone][card.number] = currentQty + 1;
  showToast(`${card.number} added to ${zone === "jump" ? "JUMP Deck" : "Main Deck"}.`);
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
function clearDeck() { if (!confirm("Clear your saved deck?")) return; deck = { leader: "", main: {}, jump: {} }; saveDeck(); showToast("Deck cleared."); }

function renderDeck() {
  const leader = selectedLeader();
  const mainTotal = mainDeckTotal(), jumpTotal = jumpDeckTotal();
  elements.deckTabCount.textContent = `${mainTotal}/${MAIN_DECK_SIZE}`;
  elements.leaderStatus.innerHTML = leader ? `${escapeHtml(leader.number)} ${colorBadgeHtml(leader.color)}` : "None selected";
  elements.mainDeckCount.textContent = `${mainTotal} / ${MAIN_DECK_SIZE}`;
  elements.jumpDeckCount.textContent = `${jumpTotal}`;
  renderDeckList(elements.mainDeckList, deck.main, "main");
  renderDeckList(elements.jumpDeckList, deck.jump, "jump");
  renderDeckMessages(leader, mainTotal);
}
function renderDeckList(container, entries, zone) {
  const rows = Object.entries(entries).map(([number, qty]) => ({ card: getCard(number), qty })).filter(row => row.card).sort((a,b) => compareDefault(a.card,b.card));
  if (!rows.length) { container.innerHTML = `<p class="deck-message">No cards yet.</p>`; return; }
  container.innerHTML = "";
  rows.forEach(({card, qty}) => {
    const row = document.createElement("article");
    row.className = "deck-row";
    row.innerHTML = `<img src="${escapeHtml(card.image)}" alt="${escapeHtml(card.number)}"><div><h3>${escapeHtml(card.number)} ${colorBadgeHtml(card.color)}</h3><p>${escapeHtml(card.set)} · ${escapeHtml(card.cardType)}${card.deckZone === "JUMP" ? " · JUMP" : ""}</p></div><div class="qty-controls"><button type="button" aria-label="Remove one ${escapeHtml(card.number)}">−</button><strong>${qty}</strong><button type="button" aria-label="Add one ${escapeHtml(card.number)}">+</button></div>`;
    row.querySelectorAll("button")[0].addEventListener("click", () => removeOne(card.number, zone));
    row.querySelectorAll("button")[1].addEventListener("click", () => addOne(card.number, zone));
    container.appendChild(row);
  });
}
function renderDeckMessages(leader, mainTotal) {
  const messages = [];
  if (!leader) messages.push(["warn", "Choose one Leader to set your deck color."]);
  if (leader) messages.push(["good", `Leader color: ${leader.color}. Only ${leader.color} cards can be added.`]);
  if (mainTotal < MAIN_DECK_SIZE) messages.push(["warn", `Main Deck needs ${MAIN_DECK_SIZE - mainTotal} more card${MAIN_DECK_SIZE - mainTotal === 1 ? "" : "s"}.`]);
  if (mainTotal === MAIN_DECK_SIZE) messages.push(["good", "Main Deck is exactly 50 cards."]);
  if (mainTotal > MAIN_DECK_SIZE) messages.push(["error", "Main Deck has too many cards."]);
  elements.deckMessages.innerHTML = messages.map(([kind, text]) => `<div class="deck-message ${kind}">${escapeHtml(text)}</div>`).join("");
}
function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { elements.toast.hidden = true; }, 2200);
}

function escapeHtml(value) { return String(value || "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
function createPlaceholderImage(cardNumber) { const safeNumber = escapeHtml(cardNumber || "Missing Image"); const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="500" height="700" viewBox="0 0 500 700"><rect width="500" height="700" rx="32" fill="#171717"/><rect x="30" y="30" width="440" height="640" rx="24" fill="#231f17" stroke="#c89a2c" stroke-width="8"/><text x="250" y="320" text-anchor="middle" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#d2a642">Image missing</text><text x="250" y="370" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" fill="#f6efe2">${safeNumber}</text></svg>`; return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`; }
