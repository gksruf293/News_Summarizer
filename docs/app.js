import { pipeline } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.6.0';

let categoryData = {};
let embeddingData = [];
let extractor = null;
let currentSelectedArticle = null;

// 초기화 함수
async function init() {
    const container = document.getElementById("results-container");
    const searchBtn = document.getElementById("searchBtn");
    
    // UI 초기화
    if (searchBtn) {
        searchBtn.disabled = true;
        searchBtn.innerText = "모델 로딩 중...";
    }
    container.innerHTML = `<div class="status-msg">AI 검색 모델(Transformers.js)을 로드하고 있습니다...</div>`;

    try {
        // 1. 임베딩 추출 모델 로드
        extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
        console.log("✅ AI Model Loaded Successfully");
        
        if (searchBtn) {
            searchBtn.disabled = false;
            searchBtn.innerText = "AI 시맨틱 검색";
        }

        // 2. 데이터 로드 (기본값: latest)
        await loadDataByDate('latest');
    } catch (err) {
        console.error("❌ 초기화 에러:", err);
        container.innerHTML = `<div class="error-msg">모델 또는 데이터를 불러오는 데 실패했습니다. 콘솔 로그를 확인해주세요.</div>`;
    }
}

// 날짜별 데이터 로드 함수
window.loadDataByDate = async function(date) {
    const container = document.getElementById("results-container");
    console.log(`fetching data for: ${date}`);

    try {
        const [catRes, embRes] = await Promise.all([
            fetch(`data/${date}/category.json`),
            fetch(`data/${date}/embedding.json`)
        ]);

        if (!catRes.ok || !embRes.ok) throw new Error(`HTTP error! status: ${catRes.status}`);

        categoryData = await catRes.json();
        embeddingData = await embRes.json();

        console.log("✅ Data Loaded:", categoryData);
        renderCards(categoryData['general'] || []);
    } catch (err) {
        console.error("❌ 데이터 로드 실패:", err);
        container.innerHTML = `<div class="error-msg">📍 ${date} 데이터를 찾을 수 없습니다. (경로: data/${date}/)</div>`;
    }
};

// 시맨틱 검색 핸들러
window.handleSearch = async function() {
    const query = document.getElementById("interestInput").value.trim();
    if (!query || !extractor) return;

    const container = document.getElementById("results-container");
    container.innerHTML = `<div class="status-msg">'${query}' 관련 뉴스를 찾는 중...</div>`;

    try {
        // 쿼리 임베딩 생성
        const output = await extractor(query, { pooling: 'mean', normalize: true });
        const userVector = Array.from(output.data);

        // 유사도 계산
        const scored = embeddingData.map(art => ({
            ...art,
            score: cosineSimilarity(userVector, art.embedding)
        })).sort((a, b) => b.score - a.score);

        renderCards(scored.slice(0, 10));
    } catch (err) {
        console.error("❌ 검색 에러:", err);
    }
};

// 코사인 유사도 함수
function cosineSimilarity(a, b) {
    let dot = 0, nA = 0, nB = 0;
    for (let i = 0; i < a.length; i++) {
        dot += a[i] * b[i];
        nA += a[i] * a[i]; nB += b[i] * b[i];
    }
    return dot / (Math.sqrt(nA) * Math.sqrt(nB));
}

// 카드 렌더링
function renderCards(articles) {
    const container = document.getElementById("results-container");
    container.innerHTML = "";
    if (articles.length === 0) {
        container.innerHTML = `<p class="status-msg">표시할 뉴스가 없습니다.</p>`;
        return;
    }

    articles.forEach(art => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
            ${art.image ? `<img src="${art.image}">` : ''}
            <div class="card-info">
                <h3>${art.title}</h3>
                <p>${art.summaries ? art.summaries.elementary.en.slice(0, 100) : (art.description || '')}...</p>
            </div>
        `;
        card.onclick = () => openModal(art);
        container.appendChild(card);
    });
}

// 모달 관련 함수
window.openModal = function(article) {
    currentSelectedArticle = article;
    document.getElementById("modal-title").innerText = article.title;
    document.getElementById("modal-link").href = article.url;
    document.getElementById("modal").style.display = "block";
    updateSummaryLevel('elementary');
};

window.updateSummaryLevel = function(level) {
    if (!currentSelectedArticle) return;
    const data = currentSelectedArticle.summaries[level];
    const summaryBox = document.getElementById("summary-text");

    summaryBox.innerHTML = `
        <div class="english-box" onclick="toggleTranslation()">
            <p class="en-text">${data.en}</p>
            <p class="ko-text" id="ko-translation" style="display:none;">🔍 ${data.ko}</p>
            <div class="hint-badge">Click to see Translation</div>
        </div>
    `;
    document.querySelectorAll(".level-btn").forEach(btn => btn.classList.remove("active"));
    document.getElementById(`btn-${level}`).classList.add("active");
};

window.toggleTranslation = () => {
    const ko = document.getElementById("ko-translation");
    if (ko) ko.style.display = ko.style.display === "none" ? "block" : "none";
};

window.closeModal = () => document.getElementById("modal").style.display = "none";

window.loadCategory = (cat, btn) => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    renderCards(categoryData[cat] || []);
};

// 페이지 로드 시 초기화
init();
