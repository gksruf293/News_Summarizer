import { pipeline } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.6.0';

let categoryData = {};
let embeddingData = [];
let extractor = null;
let currentSelectedArticle = null;

/**
 * 초기화: AI 모델 로드 및 날짜 변경 이벤트 바인딩
 */
async function init() {
    const container = document.getElementById("results-container");
    const searchBtn = document.getElementById("searchBtn");
    const datePicker = document.getElementById("datePicker");
    
    if (searchBtn) searchBtn.disabled = true;
    container.innerHTML = `<div class="status-msg">AI 모델 및 데이터를 준비 중입니다...</div>`;

    try {
        // 1. 시맨틱 검색을 위한 로컬 모델 로드
        extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
        console.log("✅ AI Model Loaded");

        // 2. 초기 데이터 로드 (latest)
        await loadDataByDate('latest');

        // 3. [버그 수정] 날짜 선택기 이벤트 리스너 등록
        if (datePicker) {
            datePicker.addEventListener('change', async (e) => {
                const selectedDate = e.target.value;
                if (selectedDate) {
                    console.log(`📅 날짜 변경 요청: ${selectedDate}`);
                    await loadDataByDate(selectedDate);
                }
            });
        }

        if (searchBtn) { 
            searchBtn.disabled = false; 
            searchBtn.innerText = "AI 시맨틱 검색"; 
        }
    } catch (err) {
        console.error("Init Error:", err);
        container.innerHTML = `<div class="error-msg">초기화 실패. 페이지를 새로고침 해주세요.</div>`;
    }
}

/**
 * 특정 날짜의 JSON 데이터를 가져오는 함수
 */
window.loadDataByDate = async function(date) {
    const container = document.getElementById("results-container");
    container.innerHTML = `<div class="status-msg">${date} 데이터를 불러오는 중...</div>`;
    
    try {
        const cacheBust = `?t=${new Date().getTime()}`;
        const [catRes, embRes] = await Promise.all([
            fetch(`./data/${date}/category.json${cacheBust}`),
            fetch(`./data/${date}/embedding.json${cacheBust}`)
        ]);
        
        if (!catRes.ok || !embRes.ok) throw new Error(`${date}의 데이터가 존재하지 않습니다.`);

        categoryData = await catRes.json();
        const embJson = await embRes.json();
        embeddingData = Array.isArray(embJson) ? embJson : [];
        
        console.log(`📊 데이터 로드 완료 | 날짜: ${date} | 임베딩: ${embeddingData.length}개`);

        // 화면 탭 및 카드 초기화 (general 우선)
        const firstCat = categoryData['general'] ? 'general' : Object.keys(categoryData)[0];
        
        // 탭 UI 활성화 상태 동기화
        document.querySelectorAll(".tab-btn").forEach(btn => {
            btn.classList.remove("active");
            if (btn.getAttribute('onclick')?.includes(`'${firstCat}'`)) {
                btn.classList.add("active");
            }
        });

        renderCards(categoryData[firstCat] || []);

    } catch (err) {
        console.error("Data Load Error:", err);
        container.innerHTML = `<div class="error-msg">⚠️ ${err.message}</div>`;
        categoryData = {};
        embeddingData = [];
    }
};

/**
 * 시맨틱 검색 함수
 */
window.handleSearch = async function() {
    const input = document.getElementById("interestInput");
    const query = input.value.trim();
    
    if (!query) return;
    if (!extractor || embeddingData.length === 0) {
        alert("데이터 로딩 중입니다.");
        return;
    }

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
        console.error("Search Error:", err);
        container.innerHTML = `<div class="error-msg">검색 중 오류가 발생했습니다.</div>`;
    }
};

/**
 * 뉴스 카드 렌더링 (이미지 에러 처리 포함)
 */
function renderCards(articles) {
    const container = document.getElementById("results-container");
    container.innerHTML = "";
    
    if (!articles || articles.length === 0) {
        container.innerHTML = `<div class="status-msg">표시할 뉴스가 없습니다.</div>`;
        return;
    }

    articles.forEach(art => {
        const card = document.createElement("div");
        card.className = "card";
        
        const summaryPreview = art.summaries?.elementary?.en || art.title;
        const scoreTag = art.score ? `<span class="score-tag">${Math.round(art.score * 100)}% 관련됨</span>` : '';

        card.innerHTML = `
            ${art.image ? `<img src="${art.image}" onerror="this.parentElement.querySelector('img').style.display='none';">` : ''}
            <div class="card-info">
                ${scoreTag}
                <h3>${art.title}</h3>
                <p>${summaryPreview.slice(0, 110)}...</p>
            </div>
        `;
        card.onclick = () => openModal(art);
        container.appendChild(card);
    });
}

function cosineSimilarity(a, b) {
    let dot = 0, nA = 0, nB = 0;
    for (let i = 0; i < a.length; i++) {
        dot += a[i] * b[i];
        nA += a[i] * a[i];
        nB += b[i] * b[i];
    }
    return dot / (Math.sqrt(nA) * Math.sqrt(nB));
}

/**
 * 모달 제어 및 레벨별 데이터 바인딩
 */
window.openModal = (article) => {
    currentSelectedArticle = article;
    document.getElementById("modal-title").innerText = article.title;
    document.getElementById("modal-link").href = article.url;
    document.getElementById("modal").style.display = "block";
    
    // 모달 열릴 때 기본으로 elementary 레벨 표시
    updateSummaryLevel('elementary');
};

window.closeModal = () => {
    document.getElementById("modal").style.display = "none";
};

// [버그 수정] 레벨 클릭 시 실제 해당 레벨 데이터로 교체
window.updateSummaryLevel = (level) => {
    if (!currentSelectedArticle || !currentSelectedArticle.summaries) return;

    const summaryData = currentSelectedArticle.summaries[level] || 
        { en: "Summary not available for this level.", ko: "해당 레벨의 요약이 없습니다." };
    
    const summaryBox = document.getElementById("summary-text");
    summaryBox.innerHTML = `
        <div class="english-box" onclick="toggleTranslation()">
            <p class="en-text">${summaryData.en}</p>
            <p class="ko-text" id="ko-translation" style="display:none;">🔍 ${summaryData.ko}</p>
            <small style="color: #3b82f6; display:block; margin-top:10px; cursor:pointer;">
                💡 문장을 클릭하면 한국어 해석이 나타납니다.
            </small>
        </div>
    `;
    
    // 버튼 활성화 상태 변경
    document.querySelectorAll(".level-btn").forEach(btn => {
        btn.classList.remove("active");
        if (btn.id === `btn-${level}`) btn.classList.add("active");
    });
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

// 초기화 시작
init();
