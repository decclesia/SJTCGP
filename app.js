// SJTCG static card image database
let allCards = [];
let visibleCards = [];
let currentModalIndex = -1;
let activeFilters = { release: "", set: "", color: "" };

const colorLetters = { Yellow: "Y", Red: "R", Blue: "B", Green: "G", Pink: "P" };
const colorOrder = { Yellow: 0, Red: 1, Blue: 2, Green: 3, Pink: 4 };

const elements = {
  searchInput: document.querySelector("#searchInput"),
  releaseFilters: document.querySelector("#releaseFilters"),
  setFilters: document.querySelector("#setFilters"),
  colorFilters: document.querySelector("#colorFilters"),
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
  modalNext: document.querySelector("#modalNext")
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  setupTheme();
  try {
    const response = await fetch("cards.json");
    if (!response.ok) throw new Error("Could not load cards.json");
    allCards = await response.json();
    allCards = sortCards(allCards, "default");
    populateFilterButtons();
    addEventListeners();
    renderCards();
  } catch (error) {
    console.error(error);
    elements.resultCount.textContent = "Could not load cards.json.";
    elements.cardGrid.innerHTML = `<div class="empty-state"><h2>Could not load cards</h2><p>Use a local web server instead of opening index.html directly.</p></div>`;
  }
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

function updateThemeButton() {
  elements.themeToggle.textContent = document.body.classList.contains("dark") ? "Light" : "Dark";
}

function addEventListeners() {
  elements.searchInput.addEventListener("input", renderCards);
  elements.sortSelect.addEventListener("change", renderCards);
  elements.resetButton.addEventListener("click", resetFilters);
  elements.modalPrev.addEventListener("click", () => showRelativeCard(-1));
  elements.modalNext.addEventListener("click", () => showRelativeCard(1));
  document.querySelectorAll("[data-close-modal]").forEach((element) => element.addEventListener("click", closeModal));
  document.addEventListener("keydown", (event) => {
    if (elements.modal.hidden) return;
    if (event.key === "Escape") closeModal();
    if (event.key === "ArrowLeft") showRelativeCard(-1);
    if (event.key === "ArrowRight") showRelativeCard(1);
  });
}

function populateFilterButtons() {
  const releases = uniqueValues(allCards.map((card) => card.release)).sort(compareRelease);
  const sets = uniqueValues(allCards.map((card) => card.set)).sort(compareText);
  const colors = uniqueValues(allCards.map((card) => card.color)).sort(compareColors);

  renderFilterGroup(elements.releaseFilters, releases, "release");
  renderFilterGroup(elements.setFilters, sets, "set");
  renderFilterGroup(elements.colorFilters, colors, "color");
}

function renderFilterGroup(container, values, type) {
  container.innerHTML = "";
  values.forEach((value) => container.appendChild(makeFilterButton(value, type)));
}

function makeFilterButton(value, type) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `filter-button ${type === "color" ? "color-button" : ""}`;
  button.dataset.filterType = type;
  button.dataset.filterValue = value;

  if (type === "color") {
    button.innerHTML = colorBadgeHtml(value);
    button.title = value;
    button.setAttribute("aria-label", `${value} cards`);
  } else {
    button.textContent = value;
  }

  button.addEventListener("click", () => {
    activeFilters[type] = activeFilters[type] === value ? "" : value;
    renderCards();
  });
  return button;
}

function updateFilterButtons() {
  document.querySelectorAll(".filter-button").forEach((button) => {
    const type = button.dataset.filterType;
    const value = button.dataset.filterValue;
    button.classList.toggle("active", activeFilters[type] === value);
    button.setAttribute("aria-pressed", activeFilters[type] === value ? "true" : "false");
  });
}

function uniqueValues(values) {
  return [...new Set(values.filter(Boolean))];
}

function renderCards() {
  const searchText = elements.searchInput.value.trim().toLowerCase();
  visibleCards = allCards.filter((card) => {
    const searchableText = [card.number, card.release, card.set, card.color].join(" ").toLowerCase();
    return (!searchText || searchableText.includes(searchText)) &&
      (!activeFilters.release || card.release === activeFilters.release) &&
      (!activeFilters.set || card.set === activeFilters.set) &&
      (!activeFilters.color || card.color === activeFilters.color);
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
    if (sortBy === "number") return compareCardNumbers(a.number, b.number);
    return compareDefault(a, b);
  });
}

function compareDefault(a, b) {
  return compareRelease(a.release, b.release) || compareCardNumbers(a.number, b.number);
}

function compareRelease(a, b) {
  const order = { ST: 0, SD: 1, PUP: 2 };
  const pa = parseRelease(a), pb = parseRelease(b);
  return (order[pa.family] ?? 50) - (order[pb.family] ?? 50) || pa.family.localeCompare(pb.family) || pa.number - pb.number;
}

function parseRelease(value) {
  const match = String(value || "").match(/^([A-Z]+)(\d*)$/);
  return { family: match ? match[1] : String(value || ""), number: match && match[2] ? Number(match[2]) : 0 };
}

function compareText(a, b) {
  return String(a || "").localeCompare(String(b || ""));
}

function compareColors(a, b) {
  return (colorOrder[a] ?? 99) - (colorOrder[b] ?? 99) || compareText(a, b);
}

function compareCardNumbers(a, b) {
  return String(a || "").localeCompare(String(b || ""), undefined, { numeric: true, sensitivity: "base" });
}

function createCardElement(card, index) {
  const article = document.createElement("article");
  article.className = "card";
  article.tabIndex = 0;
  article.setAttribute("role", "button");
  article.setAttribute("aria-label", `Open ${card.number}`);
  article.innerHTML = `<img src="${escapeHtml(card.image)}" alt="${escapeHtml(card.number)}" loading="lazy"><div><h2>${escapeHtml(card.number)}</h2><p>Release: ${escapeHtml(card.release)} · Set: ${escapeHtml(card.set)}</p><p class="card-color-line">${colorBadgeHtml(card.color)} <span>${escapeHtml(card.color)}</span></p></div>`;
  const image = article.querySelector("img");
  image.addEventListener("error", () => { image.src = createPlaceholderImage(card.number); });
  article.addEventListener("click", () => openModal(index));
  article.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openModal(index); }
  });
  return article;
}

function colorBadgeHtml(color) {
  const safeColor = escapeHtml(color || "Unknown");
  const letter = escapeHtml(colorLetters[color] || "?");
  return `<span class="color-badge color-${safeColor.toLowerCase()}" title="${safeColor}">${letter}</span>`;
}

function openModal(index) {
  currentModalIndex = index;
  showModalCard();
  elements.modal.hidden = false;
  document.body.style.overflow = "hidden";
}

function showModalCard() {
  const card = visibleCards[currentModalIndex];
  if (!card) return;
  elements.modalImage.onerror = () => { elements.modalImage.src = createPlaceholderImage(card.number); };
  elements.modalImage.src = card.image;
  elements.modalImage.alt = card.number;
  elements.modalTitle.textContent = card.number;
  elements.modalMeta.innerHTML = `Release: ${escapeHtml(card.release)} · Set: ${escapeHtml(card.set)} · Color: ${colorBadgeHtml(card.color)} ${escapeHtml(card.color)}`;
}

function showRelativeCard(offset) {
  if (!visibleCards.length) return;
  currentModalIndex = (currentModalIndex + offset + visibleCards.length) % visibleCards.length;
  showModalCard();
}

function closeModal() {
  elements.modal.hidden = true;
  document.body.style.overflow = "";
}

function resetFilters() {
  elements.searchInput.value = "";
  elements.sortSelect.value = "default";
  activeFilters = { release: "", set: "", color: "" };
  renderCards();
}

function escapeHtml(value) {
  return String(value || "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function createPlaceholderImage(cardNumber) {
  const safeNumber = escapeHtml(cardNumber || "Missing Image");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="500" height="700" viewBox="0 0 500 700"><rect width="500" height="700" rx="32" fill="#171717"/><rect x="30" y="30" width="440" height="640" rx="24" fill="#231f17" stroke="#c89a2c" stroke-width="8"/><text x="250" y="320" text-anchor="middle" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#d2a642">Image missing</text><text x="250" y="370" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" fill="#f6efe2">${safeNumber}</text></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}
