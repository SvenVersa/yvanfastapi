const API_URL = "https://yvanfastapi.vercel.app/api";
const API_KEY = "omega_level_clearance";

let globalRoster = [];

const selectA = document.getElementById("fighter-a-select");
const selectB = document.getElementById("fighter-b-select");
const statsA = document.getElementById("fighter-a-stats");
const statsB = document.getElementById("fighter-b-stats");
const simulateBtn = document.getElementById("simulate-btn");
const battleLog = document.getElementById("battle-log");

async function loadRoster() {
    try {
        // Fetching heroes (if you have a separate villains endpoint, you can fetch both and combine them)
        const response = await fetch(`${API_URL}/heroes`, {
            headers: { "x-api-key": API_KEY }
        });
        
        if (!response.ok) throw new Error("Security clearance rejected.");
        
        globalRoster = await response.json();
        populateDropdowns();
    } catch (error) {
        battleLog.classList.remove("hidden");
        battleLog.innerHTML = `<h3 style="color: var(--primary-red);">ERROR</h3><p>${error.message}</p>`;
    }
}

function populateDropdowns() {
    // Sort alphabetically by alias
    globalRoster.sort((a, b) => a.alias.localeCompare(b.alias));
    
    globalRoster.forEach(character => {
        // Create option for Fighter 1
        const optionA = document.createElement("option");
        optionA.value = character.id;
        optionA.textContent = character.alias;
        selectA.appendChild(optionA);
        
        // Create option for Fighter 2
        const optionB = document.createElement("option");
        optionB.value = character.id;
        optionB.textContent = character.alias;
        selectB.appendChild(optionB);
    });
}

function updateFighterCard(selectElement, statsCard) {
    const selectedId = selectElement.value;
    
    // Hide stats if no character is selected
    if (!selectedId) {
        statsCard.classList.add("hidden");
        checkReadyState();
        return;
    }

    // Find the character and update the HTML
    const fighter = globalRoster.find(c => c.id == selectedId);
    statsCard.querySelector(".powers-val").textContent = fighter.primary_powers || "Classified";
    statsCard.querySelector(".weakness-val").textContent = fighter.tactical_vulnerability || "Classified";
    statsCard.classList.remove("hidden");
    
    checkReadyState();
}

function checkReadyState() {
    // Enable the battle button only if both fighters are selected AND they aren't the exact same person
    if (selectA.value && selectB.value && selectA.value !== selectB.value) {
        simulateBtn.disabled = false;
    } else {
        simulateBtn.disabled = true;
    }
}

// Listen for dropdown changes
selectA.addEventListener("change", () => updateFighterCard(selectA, statsA));
selectB.addEventListener("change", () => updateFighterCard(selectB, statsB));

// Listen for the Simulate button
simulateBtn.addEventListener("click", runSimulation);

function runSimulation() {
    const fighterA = globalRoster.find(c => c.id == selectA.value);
    const fighterB = globalRoster.find(c => c.id == selectB.value);
    
    simulateBtn.disabled = true; // Lock button during battle
    battleLog.innerHTML = `<h3>${fighterA.alias} VS ${fighterB.alias}</h3>`;
    battleLog.classList.remove("hidden");
    
    // Stagger the battle text to make it feel live
    setTimeout(() => {
        logAction(`<strong>TURN 1:</strong> ${fighterA.alias} initiates combat utilizing ${fighterA.primary_powers.toLowerCase()}!`);
    }, 800);
    
    setTimeout(() => {
        logAction(`<strong>TURN 2:</strong> ${fighterB.alias} retaliates, exploiting ${fighterA.alias}'s ${fighterA.tactical_vulnerability.toLowerCase()}!`);
    }, 2400);
    
    setTimeout(() => {
        // RNG logic to determine winner
        const winner = Math.random() > 0.5 ? fighterA : fighterB;
        const loser = winner === fighterA ? fighterB : fighterA;
        
        logAction(`<br><strong style="font-size: 1.5em; color: var(--primary-red);">K.O.! ${winner.alias} dominates ${loser.alias}!</strong>`);
        simulateBtn.disabled = false; // Unlock button for next fight
    }, 4200);
}

function logAction(text) {
    const p = document.createElement("p");
    p.innerHTML = text;
    battleLog.appendChild(p);
}

// Start everything when the page loads
document.addEventListener("DOMContentLoaded", loadRoster);