(() => {
  "use strict";
  const root = "https://sjtcg-private-sim.sjtcg-simulator.workers.dev/database/";
  const page = document.documentElement.dataset.databaseGateway;
  if (page !== "cards" && page !== "energy") return;
  // Only these two fixed destinations are eligible for an automatic redirect.
  const destination = new URL(page === "energy" ? "energy.html" : "", root);
  destination.search = window.location.search;
  destination.hash = window.location.hash;
  const link = document.getElementById("databaseLink");
  if (link) link.href = destination.href;
  window.location.replace(destination.href);
})();
