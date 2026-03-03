import { pipeline } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.6.0';

let categoryData = {};
let embeddingData = [];
let extractor = null;
let currentSelectedArticle = null;

async function init() {
    const container = document.getElementById("results-container");
    container.innerHTML = `<div class="status-msg">Loading AI Study Model...</div>`;

    try {
        extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
        console.log("✅ AI Model Loaded");
        await loadDataByDate('latest');
    } catch (err) {
        console.error("Init Error:", err);
    }
}

/* 날짜별 데이터 로드 */
window.loadDataByDate = async function(date) {
    const container = document.getElementById("results-container");
    try {
        const [catRes, embRes] = await Promise.all([
            fetch(`data/${date}/category.json`),
            fetch(`data/${date}/embedding.json`)
        ]);

        if (!catRes.ok) throw new Error("No data");

        categoryData = await catRes.json();
        embeddingData = await embRes.json();

        const activeTab = document.querySelector(".tab-btn.active").innerText.toLowerCase();
        renderCards(categoryData['general'] || []); 
    } catch (err) {
        container.innerHTML = `<div class="error-msg">📍 ${date} 데이터를 찾을 수 없습니다.</div>`;
    }
};

/* 검색 기능 */
window.handleSearch = async function() {
    const query = document.getElementById("interestInput").value.trim();
    if (!query || !extractor) return;

    const output = await extractor(query, { pooling: 'mean', normalize: true });
    const userVector = Array.from(output.data);

    const scored = embeddingData.map(art => ({
        ...art,
        score: cosineSimilarity(userVector, art.embedding)
    })).sort((a, b) => b.score - a.score);

    renderCards(scored.slice(0, 10));
};

function cosineSimilarity(a, b) {
    let dot = 0, nA = 0, nB = 0;
    for (let i = 0; i < a.length; i++) {
        dot += a[i] * b[i];
        nA += a[i] * a[i]; nB += b[i] * b[i];
    }
    return dot / (Math.sqrt(nA) * Math.sqrt(nB));
}

/* 카드 렌더링 */
function renderCards(articles) {
    const container = document.getElementById("results-container");
    container.innerHTML = "";
    articles.forEach(art => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
            ${art.image ? `<img src="${art.image}">` : ''}
            <div class="card-info">
                <h3>${art.title}</h3>
                <p>${art.summaries ? art.summaries.elementary.en.slice(0, 100) : ''}...</p>
            </div>
        `;
        card.onclick = () => openModal(art);
        container.appendChild(card);
    });
}

/* 수준별 요약 업데이트 (클릭 시 번역 기능 포함) */
window.updateSummaryLevel = function(level) {
    if (!currentSelectedArticle) return;
    const data = currentSelectedArticle.summaries[level];
    const summaryBox = document.getElementById("summary-text");

    // 영문과 한글 번역 배치
    summaryBox.innerHTML = `
        <div class="english-box" onclick="toggleTranslation()">
            <p class="en-text">${data.en}</p>
            <p class="ko-text" id="ko-translation">🔍 ${data.ko}</p>
            <div class="hint-badge">Click to see Translation</div>
        </div>
    `;

    document.querySelectorAll(".level-btn").forEach(btn => btn.classList.remove("active"));
    document.getElementById(`btn-${level}`).classList.add("active");
};

window.toggleTranslation = function() {
    const koText = document.getElementById("ko-translation");
    koText.style.display = (koText.style.display === "none" || koText.style.display === "") ? "block" : "none";
};

window.openModal = function(article) {
    currentSelectedArticle = article;
    document.getElementById("modal-title").innerText = article.title;
    document.getElementById("modal-link").href = article.url;
    document.getElementById("modal").style.display = "block";
    updateSummaryLevel('elementary');
};

window.closeModal = () => document.getElementById("modal").style.display = "none";

window.loadCategory = (cat, btn) => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    renderCards(categoryData[cat] || []);
};

document.getElementById('datePicker').addEventListener('change', (e) => loadDataByDate(e.target.value));

init();
