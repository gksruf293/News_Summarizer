import { pipeline } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.6.0';

let categoryData = {};
let embeddingData = [];
let extractor = null;
let currentSelectedArticle = null;

/**
 * [1] 초기화: AI 모델 로드 및 이벤트 바인딩
 */
async function init() {
    const container = document.getElementById("results-container");
    const searchBtn = document.getElementById("searchBtn");
    const datePicker = document.getElementById("datePicker");
    
    if (searchBtn) searchBtn.disabled = true;
    container.innerHTML = `<div class="status-msg">AI 모델 로딩 중...</div>`;

    try {
        // AI 모델 로드
        extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
        console.log("✅ AI Model Loaded");

        // 초기 데이터 로드 (기본값: latest)
        await loadDataByDate('latest');

        // [날짜 변경 버그 해결] 리스너 등록
        if (datePicker) {
            datePicker.addEventListener('change', (e) => {
                const selectedDate = e.target.value; 
                if (selectedDate) {
                    console.log("📅 날짜 변경 감지:", selectedDate);
                    loadDataByDate(selectedDate);
                }
            });
        }

        if (searchBtn) { 
            searchBtn.disabled = false; 
            searchBtn.innerText = "AI 시맨틱 검색"; 
        }
    } catch (err) {
        console.error("Init Error:", err);
        container.innerHTML = `<div class="error-msg">초기화 실패.</div>`;
    }
}

/**
 * [2] 데이터 로드 함수 (window에 등록하여 HTML 호출 허용)
 */
window.loadDataByDate = async function(date) {
    const container = document.getElementById("results-container");
    try {
        const cacheBust = `?t=${new Date().getTime()}`;
        const [catRes, embRes] = await Promise.all([
            fetch(`./data/${date}/category.json${cacheBust}`),
            fetch(`./data/${date}/embedding.json${cacheBust}`)
        ]);

        if (!catRes.ok) throw new Error(`${date} 데이터를 찾을 수 없습니다.`);

        categoryData = await catRes.json();
        const embJson = await embRes.json();
        embeddingData = Array.isArray(embJson) ? embJson : [];
        
        console.log(`📊 ${date} 로드 완료 | 임베딩: ${embeddingData.length}개`);

        // 화면 탭 초기화 (전체/General)
        const firstCat = categoryData['general'] ? 'general' : Object.keys(categoryData)[0];
        renderCards(categoryData[firstCat] || []);

    } catch (err) {
        console.error("Data Load Error:", err);
        container.innerHTML = `<div class="error-msg">⚠️ ${err.message}</div>`;
    }
};

/**
 * [3] 레벨별 요약 업데이트 (Level 1, 2, 3 버튼 클릭 시 호출)
 */
window.updateSummaryLevel = function(level) {
    if (!currentSelectedArticle || !currentSelectedArticle.summaries) {
        console.error("데이터가 없습니다.");
        return;
    }

    const data = currentSelectedArticle.summaries[level];
    if (!data) return;

    const summaryBox = document.getElementById("summary-text");
    summaryBox.innerHTML = `
        <div class="english-box" onclick="toggleTranslation()">
            <p class="en-text" style="font-size: 1.1rem; line-height: 1.6;">${data.en}</p>
            <p class="ko-text" id="ko-translation" style="display:none; color: #666; margin-top: 10px; border-top: 1px dashed #ccc; pt-2;">🔍 ${data.ko}</p>
            <small style="color: #3b82f6; display:block; margin-top:15px; cursor:pointer;">
                💡 문장을 클릭하면 한국어 해석이 나타납니다.
            </small>
        </div>
    `;

    // 버튼 활성화 상태 표시 (btn-elementary, btn-middle, btn-high)
    document.querySelectorAll(".level-btn").forEach(btn => btn.classList.remove("active"));
    const activeBtn = document.getElementById(`btn-${level}`);
    if (activeBtn) activeBtn.classList.add("active");
};

/**
 * [4] 시맨틱 검색 함수
 */
window.handleSearch = async function() {
    const input = document.getElementById("interestInput");
    const query = input.value.trim();
    
    if (!query || !extractor) return;

    const container = document.getElementById("results-container");
    container.innerHTML = `<div class="status-msg">'${query}' 관련 뉴스 분석 중...</div>`;

    try {
        const output = await extractor(query, { pooling: 'mean', normalize: true });
        const userVector = Array.from(output.data);

        const scored = embeddingData.map(art => ({
            ...art,
            score: cosineSimilarity(userVector, art.embedding)
        })).sort((a, b) => b.score - a.score);

        renderCards(scored.slice(0, 15));
    } catch (err) {
        container.innerHTML = `<div class="error-msg">검색 중 오류가 발생했습니다.</div>`;
    }
};

/**
 * 뉴스 카드 렌더링
 */
function renderCards(articles) {
    const container = document.getElementById("results-container");
    container.innerHTML = "";
    
    articles.forEach(art => {
        const card = document.createElement("div");
        card.className = "card";
        const preview = art.summaries?.elementary?.en || art.title;
        
        card.innerHTML = `
            ${art.image ? `<img src="${art.image}" onerror="this.style.display='none'">` : ''}
            <div class="card-info">
                <h3>${art.title}</h3>
                <p>${preview.slice(0, 100)}...</p>
            </div>
        `;
        card.onclick = () => openModal(art);
        container.appendChild(card);
    });
}

window.openModal = (article) => {
    currentSelectedArticle = article;
    document.getElementById("modal-title").innerText = article.title;
    document.getElementById("modal-link").href = article.url;
    document.getElementById("modal").style.display = "block";
    // 기본 레벨 1 표시
    window.updateSummaryLevel('elementary');
};

window.closeModal = () => {
    document.getElementById("modal").style.display = "none";
};

window.toggleTranslation = () => {
    const ko = document.getElementById("ko-translation");
    if (ko) ko.style.display = ko.style.display === "none" ? "block" : "none";
};

window.loadCategory = (cat, btn) => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    renderCards(categoryData[cat] || []);
};

function cosineSimilarity(a, b) {
    let dot = 0, nA = 0, nB = 0;
    for (let i = 0; i < a.length; i++) {
        dot += a[i] * b[i];
        nA += a[i] * a[i];
        nB += b[i] * b[i];
    }
    return dot / (Math.sqrt(nA) * Math.sqrt(nB));
}

init();
