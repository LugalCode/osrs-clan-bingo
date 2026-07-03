let currentTeam = null;
let boardData = null;

async function loadData() {
  const res = await fetch(`data.json?t=${Date.now()}`);
  boardData = await res.json();

  const updatedAt = new Date(boardData.generated_at);
  document.getElementById("updated-at").textContent =
    `Last updated: ${updatedAt.toLocaleString()}`;

  const teamNames = Object.keys(boardData.teams);
  renderTabs(teamNames);
  currentTeam = teamNames[0];
  renderBoard(currentTeam);
}

function renderTabs(teamNames) {
  const nav = document.getElementById("team-tabs");
  nav.innerHTML = "";
  teamNames.forEach((name) => {
    const btn = document.createElement("button");
    btn.className = "tab-button";
    btn.textContent = name;
    btn.onclick = () => {
      currentTeam = name;
      renderBoard(name);
    };
    nav.appendChild(btn);
  });
}

function renderBoard(teamName) {
  document.querySelectorAll(".tab-button").forEach((btn) => {
    btn.classList.toggle("active", btn.textContent === teamName);
  });

  const tiles = boardData.teams[teamName];
  const overlay = document.getElementById("tile-overlay");
  overlay.innerHTML = "";

  const tileCount = Object.keys(tiles).length;
  let completeCount = 0;

  for (let i = 1; i <= tileCount; i++) {
    const tile = tiles[`Tile ${i}`];
    const cell = document.createElement("div");
    cell.className = "tile-cell";
    if (tile && tile.complete) {
      completeCount++;
      const dim = document.createElement("div");
      dim.className = "dim-layer";
      cell.appendChild(dim);

      const skull = document.createElement("img");
      skull.className = "skull";
      skull.src = "skull.png";
      skull.alt = "Complete";
      cell.appendChild(skull);
    }
    overlay.appendChild(cell);
  }

  document.getElementById("progress-summary").textContent =
    `${teamName}: ${completeCount}/${tileCount} tiles complete`;
}

loadData();
