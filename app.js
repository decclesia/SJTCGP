let allCards = [];
let currentCards = [];
let currentModalIndex = -1;

const elements = {
  searchInput: document.querySelector("#searchInput"),
  releaseFilter: document.querySelector("#releaseFilter"),
  setFilter: document.querySelector("#setFilter"),
  sortSelect: document.querySelector("#sortSelect"),
  resetButton: document.querySelector("#resetButton"),
  resultCount: document.querySelector("#resultCount"),
  cardGrid: document.querySelector("#cardGrid"),
  emptyState: document.querySelector("#emptyState"),
  modal: document.querySelector("#cardModal"),
  modalImage: document.querySelector("#modalImage"),
  modalTitle: document.querySelector("#modalTitle"),
  modalMeta: document.querySelector("#modalMeta"),
  previousCardButton: document.querySelector("#previousCardButton"),
  nextCardButton: document.querySelector("#nextCardButton"),
  releaseButtons: document.querySelector("#releaseButtons"),
  setButtons: document.querySelector("#setButtons"),
  themeToggle: document.querySelector("#themeToggle"),
  themeIcon: document.querySelector("#themeIcon"),
  themeText: document.querySelector("#themeText")
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  applySavedTheme();

  try {
    const response = await fetch("cards.json");
    if (!response.ok) throw new Error("Could not load cards.json");

    allCards = await response.json();

    populateFilters();
    addEventListeners();
    renderCards();
  } catch (error) {
    console.error(error);
    elements.resultCount.textContent = "Could not load cards.json.";
    elements.cardGrid.innerHTML = `
      <div class="empty-state">
        <h2>Could not load cards</h2>
        <p>Use a local web server or GitHub Pages.</p>
      </div>
    `;
  }
}

function addEventListeners() {
  [
    elements.searchInput,
    elements.releaseFilter,
    elements.setFilter,
    elements.sortSelect
  ].forEach((element) => {
    element.addEventListener("input", renderCards);
    element.addEventListener("change", renderCards);
  });

  elements.resetButton.addEventListener("click", resetFilters);
  elements.themeToggle.addEventListener("click", toggleTheme);

  elements.previousCardButton.addEventListener("click", showPreviousCard);
  elements.nextCardButton.addEventListener("click", showNextCard);

  document.querySelectorAll("[data-close-modal]").forEach((element) => {
    element.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", (event) => {
    if (elements.modal.hidden) return;

    if (event.key === "Escape") closeModal();
    if (event.key === "ArrowLeft") showPreviousCard();
    if (event.key === "ArrowRight") showNextCard();
  });
}

function populateFilters() {
  const releases = sortReleases(uniqueValues(allCards.map((card) => card.release)));
  const sets = uniqueValues(allCards.map((card) => card.set)).sort(compareText);

  fillSelect(elements.releaseFilter, releases);
  fillSelect(elements.setFilter, sets);

  createFilterButtons(elements.releaseButtons, releases, elements.releaseFilter);
  createFilterButtons(elements.setButtons, sets, elements.setFilter);
}

function fillSelect(selectElement, values) {
  const firstOption = selectElement.querySelector("option");
  selectElement.innerHTML = "";
  selectElement.appendChild(firstOption);

  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    selectElement.appendChild(option);
  });
}

function createFilterButtons(container, values, linkedSelect) {
  container.innerHTML = "";

  const allButton = createFilterButton("All", "", linkedSelect);
  container.appendChild(allButton);

  values.forEach((value) => {
    container.appendChild(createFilterButton(value, value, linkedSelect));
  });

  updateFilterButtons();
}

function createFilterButton(label, value, linkedSelect) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "filter-pill";
  button.textContent = label;
  button.dataset.value = value;

  button.addEventListener("click", () => {
    linkedSelect.value = value;
    renderCards();
  });

  return button;
}

function updateFilterButtons() {
  updateButtonGroup(elements.releaseButtons, elements.releaseFilter.value);
  updateButtonGroup(elements.setButtons, elements.setFilter.value);
}

function updateButtonGroup(container, selectedValue) {
  container.querySelectorAll(".filter-pill").forEach((button) => {
    button.classList.toggle("active", button.dataset.value === selectedValue);
  });
}

function uniqueValues(values) {
  return [...new Set(values.filter(Boolean))];
}

function renderCards() {
  const searchText = elements.searchInput.value.trim().toLowerCase();
  const release = elements.releaseFilter.value;
  const set = elements.setFilter.value;

  let cards = allCards.filter((card) => {
    const searchableText = [card.number, card.release, card.set].join(" ").toLowerCase();
    return (
      (!searchText || searchableText.includes(searchText)) &&
      (!release || card.release === release) &&
      (!set || card.set === set)
    );
  });

  cards = sortCards(cards, elements.sortSelect.value);
  currentCards = cards;

  elements.cardGrid.innerHTML = "";
  cards.forEach((card, index) => {
    elements.cardGrid.appendChild(createCardElement(card, index));
  });

  elements.resultCount.textContent = `${cards.length} card${cards.length === 1 ? "" : "s"} found`;
  elements.emptyState.hidden = cards.length !== 0;
  updateFilterButtons();
}

function sortCards(cards, sortBy) {
  return [...cards].sort((a, b) => {
    if (sortBy === "release") {
      return compareText(a.release, b.release) || compareCardNumbers(a.number, b.number);
    }

    if (sortBy === "set") {
      return compareText(a.set, b.set) || compareCardNumbers(a.number, b.number);
    }

    if (sortBy === "number") {
      return compareCardNumbers(a.number, b.number);
    }

    return compareDefaultOrder(a, b);
  });
}

function compareDefaultOrder(a, b) {
  return (
    releaseRank(a.release) - releaseRank(b.release) ||
    compareReleaseNumber(a.release, b.release) ||
    compareCardNumbers(a.number, b.number)
  );
}

function releaseRank(release) {
  if (/^ST\d+/i.test(release)) return 1;
  if (/^SD\d+/i.test(release)) return 2;
  if (/^PUP$/i.test(release)) return 3;
  return 4;
}

function compareReleaseNumber(a, b) {
  const numberA = Number(String(a).match(/\d+/)?.[0] || 0);
  const numberB = Number(String(b).match(/\d+/)?.[0] || 0);
  return numberA - numberB;
}

function sortReleases(releases) {
  return [...releases].sort((a, b) => {
    return (
      releaseRank(a) - releaseRank(b) ||
      compareReleaseNumber(a, b) ||
      compareText(a, b)
    );
  });
}

function createCardElement(card, index) {
  const article = document.createElement("article");
  article.className = "card";
  article.tabIndex = 0;
  article.setAttribute("role", "button");
  article.setAttribute("aria-label", `Open ${card.number}`);

  article.innerHTML = `
    <img src="${escapeHtml(card.image)}" alt="${escapeHtml(card.number)}" loading="lazy">
    <div>
      <h2>${escapeHtml(card.number)}</h2>
      <p>Release: ${escapeHtml(card.release)} · Set: ${escapeHtml(card.set)}</p>
    </div>
  `;

  const image = article.querySelector("img");
  image.addEventListener("error", () => {
    image.src = createPlaceholderImage(card.number);
  });

  article.addEventListener("click", () => openModal(index));
  article.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openModal(index);
    }
  });

  return article;
}

function openModal(index) {
  currentModalIndex = index;
  showCardInModal(currentCards[currentModalIndex]);

  elements.modal.hidden = false;
  document.body.style.overflow = "hidden";
}

function showCardInModal(card) {
  if (!card) return;

  elements.modalImage.src = card.image;
  elements.modalImage.alt = card.number;
  elements.modalImage.onerror = () => {
    elements.modalImage.src = createPlaceholderImage(card.number);
  };

  elements.modalTitle.textContent = card.number;
  elements.modalMeta.textContent = `Release: ${card.release} · Set: ${card.set}`;
}

function showPreviousCard() {
  if (!currentCards.length) return;
  currentModalIndex = (currentModalIndex - 1 + currentCards.length) % currentCards.length;
  showCardInModal(currentCards[currentModalIndex]);
}

function showNextCard() {
  if (!currentCards.length) return;
  currentModalIndex = (currentModalIndex + 1) % currentCards.length;
  showCardInModal(currentCards[currentModalIndex]);
}

function closeModal() {
  elements.modal.hidden = true;
  document.body.style.overflow = "";
}

function resetFilters() {
  elements.searchInput.value = "";
  elements.releaseFilter.value = "";
  elements.setFilter.value = "";
  elements.sortSelect.value = "default";
  renderCards();
}

function applySavedTheme() {
  const savedTheme = localStorage.getItem("sjtcg-theme");

  if (savedTheme === "dark") {
    document.body.classList.add("dark-mode");
  }

  updateThemeButton();
}

function toggleTheme() {
  document.body.classList.toggle("dark-mode");
  localStorage.setItem("sjtcg-theme", document.body.classList.contains("dark-mode") ? "dark" : "light");
  updateThemeButton();
}

function updateThemeButton() {
  const isDark = document.body.classList.contains("dark-mode");
  elements.themeIcon.textContent = isDark ? "☀️" : "🌙";
  elements.themeText.textContent = isDark ? "Light" : "Dark";
}

function compareText(a, b) {
  return String(a || "").localeCompare(String(b || ""));
}

function compareCardNumbers(a, b) {
  return String(a || "").localeCompare(String(b || ""), undefined, {
    numeric: true,
    sensitivity: "base"
  });
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function createPlaceholderImage(cardNumber) {
  const safeNumber = escapeHtml(cardNumber || "Missing Image");
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="500" height="700" viewBox="0 0 500 700">
      <rect width="500" height="700" rx="32" fill="#f1ede4"/>
      <rect x="30" y="30" width="440" height="640" rx="24" fill="#ffffff" stroke="#ddd4c2" stroke-width="8"/>
      <text x="250" y="320" text-anchor="middle" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#706a5e">Image missing</text>
      <text x="250" y="370" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" fill="#706a5e">${safeNumber}</text>
    </svg>
  `;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}
