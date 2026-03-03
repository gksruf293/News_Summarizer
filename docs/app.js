import { pipeline } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.6.0';

let categoryData = {};
let embeddingData = [];
let extractor = null; // 임베딩 추출기
let currentSelectedArticle = null;

/**
 * 초기화: 모델 로드 및 최신 데이터 로드
 */
async function init() {
    const container = document.getElementById("results-container");
    const searchBtn = document.getElementById("searchBtn");
    
    // 1. 모델 로딩 중 UI 표시
    searchBtn.disabled = true;
    searchBtn.innerText = "모델 로딩 중...";
    container.innerHTML = `<div class="status-msg">AI 검색 모델을 준비 중입니다. 잠시만 기다려 주세요...</div>`;

    try {
        // 브라우저용 임베딩 모델 로드 (all-MiniLM-L6-v2)
        extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
        console.log("✅ AI 모델 로드 완료");
        
        searchBtn.disabled = false;
        searchBtn.innerText = "AI 시맨틱 검색";

        // 2. 초기 데이터 로드
        await loadDataByDate('latest');
    } catch (err) {
        console.error("모델 로드 실패:", err);
        container.innerHTML = `<div class="error-msg">모델 로드에 실패했습니다. 페이지를 새로고침 해주세요.</div>`;
    }
}

/**
 * 시맨틱 검색 핵심 로직
 */
window.handleSearch = async function() {
    const query = document.getElementById("interestInput").value.trim();
    if (!query) return;
    if (!extractor) {
        alert("모델이 아직 준비되지 않았습니다.");
        return;
    }

    const container = document.getElementById("results-container");
    container.innerHTML = `<div class="status-msg">'${query}'에 대한 의미 기반 검색을 수행 중입니다...</div>`;

    try {
        // 1. 사용자 입력 쿼리를 벡터로 변환
        // pooling: 'mean'과 normalize: true를 사용하여 유닛 벡터 생성
        const output = await extractor(query, { pooling: 'mean', normalize: true });
        const userVector = Array.from(output.data);

        // 2. 파이썬에서 생성된 embedding.json 데이터와 비교
        if (!embeddingData || embeddingData.length === 0) {
            container.innerHTML = `<div class="error-msg">검색 가능한 데이터가 없습니다.</div>`;
            return;
        }

        const scored = embeddingData.map(article => {
            // 코사인 유사도 계산
            const score = cosineSimilarity(userVector, article.embedding);
            return { ...article, score: score };
        });

        // 3. 유사도 순 정렬 (높은 순) 후 상위 10개 추출
        scored.sort((a, b) => b.score - a.score);
        
        // 유사도가 너무 낮은 결과(예: 0.1 이하)는 필터링하거나 표시
        const topResults = scored.slice(0, 10);
        
        renderCards(topResults);
        
        // 검색 결과 안내 메시지 추가
        const searchInfo = document.createElement("div");
        searchInfo.className = "search-info-tag";
        searchInfo.innerText = `'${query}'와 가장 의미가 가까운 뉴스입니다.`;
        container.prepend(searchInfo);

    } catch (err) {
        console.error("검색 중 오류:", err);
        container.innerHTML = `<div class="error-msg">검색 처리 중 오류가 발생했습니다.</div>`;
    }
};

/**
 * 코사인 유사도 연산
 */
function cosineSimilarity(vecA, vecB) {
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;
    for (let i = 0; i < vecA.length; i++) {
        dotProduct += vecA[i] * vecB[i];
        normA += vecA[i] * vecA[i];
        normB += vecB[i] * vecB[i];
    }
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

/**
 * 카드 렌더링 함수
 */
function renderCards(articles) {
    const container = document.getElementById("results-container");
    container.innerHTML = "";

    if (articles.length === 0) {
        container.innerHTML = `<div class="status-msg">검색 결과가 없습니다.</div>`;
        return;
    }

    articles.forEach(art => {
        const card = document.createElement("div");
        card.className = "card";
        // 유사도 점수가 있는 경우 표시 (디버깅 및 사용자 안내용)
        const scoreTag = art.score ? `<span class="score-tag">Match: ${Math.round(art.score * 100)}%</span>` : '';
        
        card.innerHTML = `
            ${art.image ? `<img src="${art.image}" alt="news">` : ''}
            <div class="card-info">
                ${scoreTag}
                <h3>${art.title}</h3>
                <p>${art.summaries ? art.summaries.elementary.en.substring(0, 100) : art.description || ''}...</p>
            </div>
        `;
        card.onclick = () => openModal(art);
        container.appendChild(card);
    });
}

// ... (기타 모달 및 날짜 로드 함수는 이전과 동일) ...

window.loadDataByDate = async function(date) {
    try {
        const [catRes, embRes] = await Promise.all([
            fetch(`data/${date}/category.json`),
            fetch(`data/${date}/embedding.json`)
        ]);
        if (!catRes.ok || !embRes.ok) throw new Error("데이터 없음");
        categoryData = await catRes.json();
        embeddingData = await embRes.json();
        renderCards(categoryData['general'] || []);
    } catch (err) {
        document.getElementById("results-container").innerHTML = `<div class="error-msg">데이터를 불러올 수 없습니다.</div>`;
    }
};

window.openModal = function(article) {
    currentSelectedArticle = article;
    document.getElementById("modal-title").innerText = article.title;
    document.getElementById("modal-link").href = article.url;
    document.getElementById("modal").style.display = "block";
    updateSummaryLevel('elementary');
};

window.updateSummaryLevel = function(level) {
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
    ko.style.display = ko.style.display === "none" ? "block" : "none";
};

window.closeModal = () => document.getElementById("modal").style.display = "none";

// 초기화 실행
init();
