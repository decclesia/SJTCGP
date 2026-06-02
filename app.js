let allCards = [];

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
  modalMeta: document.querySelector("#modalMeta")
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
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

  document.querySelectorAll("[data-close-modal]").forEach((element) => {
    element.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeModal();
  });
}

function populateFilters() {
  fillSelect(elements.releaseFilter, uniqueValues(allCards.map((card) => card.release)));
  fillSelect(elements.setFilter, uniqueValues(allCards.map((card) => card.set)));
}

function fillSelect(selectElement, values) {
  const firstOption = selectElement.querySelector("option");
  selectElement.innerHTML = "";
  selectElement.appendChild(firstOption);

  values.sort(compareText).forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    selectElement.appendChild(option);
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

  elements.cardGrid.innerHTML = "";
  cards.forEach((card) => elements.cardGrid.appendChild(createCardElement(card)));

  elements.resultCount.textContent = `${cards.length} card${cards.length === 1 ? "" : "s"} found`;
  elements.emptyState.hidden = cards.length !== 0;
}

function sortCards(cards, sortBy) {
  return [...cards].sort((a, b) => {
    if (sortBy === "release") {
      return compareText(a.release, b.release) || compareCardNumbers(a.number, b.number);
    }
    if (sortBy === "set") {
      return compareText(a.set, b.set) || compareCardNumbers(a.number, b.number);
    }
    return compareCardNumbers(a.number, b.number);
  });
}

function createCardElement(card) {
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

  article.addEventListener("click", () => openModal(card));
  article.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openModal(card);
    }
  });

  return article;
}

function openModal(card) {
  elements.modalImage.src = card.image;
  elements.modalImage.alt = card.number;
  elements.modalImage.onerror = () => {
    elements.modalImage.src = createPlaceholderImage(card.number);
  };

  elements.modalTitle.textContent = card.number;
  elements.modalMeta.textContent = `Release: ${card.release} · Set: ${card.set}`;
  elements.modal.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeModal() {
  elements.modal.hidden = true;
  document.body.style.overflow = "";
}

function resetFilters() {
  elements.searchInput.value = "";
  elements.releaseFilter.value = "";
  elements.setFilter.value = "";
  elements.sortSelect.value = "number";
  renderCards();
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
      <rect width="500" height="700" rx="32" fill="#eef2f8"/>
      <rect x="30" y="30" width="440" height="640" rx="24" fill="#ffffff" stroke="#dce3ef" stroke-width="8"/>
      <text x="250" y="320" text-anchor="middle" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#68738a">Image missing</text>
      <text x="250" y="370" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" fill="#68738a">${safeNumber}</text>
    </svg>
  `;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}
