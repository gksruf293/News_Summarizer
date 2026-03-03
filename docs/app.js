let everythingData = [];
const TOP_K = 10;

/* Load embeddings once */
fetch("data/everything_embeddings.json")
    .then(res => res.json())
    .then(data => {
        everythingData = data;
        console.log("Loaded articles:", everythingData.length);
    });

/* Cosine similarity */
function cosineSimilarity(a, b) {
    let dot = 0.0;
    let normA = 0.0;
    let normB = 0.0;

    for (let i = 0; i < a.length; i++) {
        dot += a[i] * b[i];
        normA += a[i] * a[i];
        normB += b[i] * b[i];
    }

    return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

/* Generate simple interest embedding via local vector trick */
/* NOTE: Since we cannot call OpenAI from browser safely,
   we approximate embedding using article title similarity fallback.
   (True embedding-based search works if you later add safe embedding endpoint.) */

function simpleTextEmbedding(text) {
    const vector = new Array(300).fill(0);
    for (let i = 0; i < text.length; i++) {
        vector[i % 300] += text.charCodeAt(i);
    }
    return vector;
}

/* Search handler */
function handleSearch() {

    const interest = document.getElementById("interestInput").value.trim();
    if (!interest || everythingData.length === 0) return;

    const userEmbedding = simpleTextEmbedding(interest);

    const scored = everythingData.map(article => {
        return {
            ...article,
            score: cosineSimilarity(userEmbedding, article.embedding.slice(0, 300))
        };
    });

    scored.sort((a, b) => b.score - a.score);

    const topK = scored.slice(0, TOP_K);

    renderResults(topK);
}

/* Render cards */
function renderResults(articles) {

    const container = document.getElementById("results-container");
    container.innerHTML = "";

    articles.forEach(article => {

        const card = document.createElement("div");
        card.className = "card";

        card.innerHTML = `
            ${article.image ? `<img src="${article.image}">` : ""}
            <h3>${article.title}</h3>
            <p>${article.summary || ""}</p>
        `;

        card.onclick = () => openModal(article);

        container.appendChild(card);
    });
}

/* Modal open */
function openModal(article) {

    document.getElementById("modal-title").innerText = article.title;
    document.getElementById("modal-text").innerText =
        article.full_text || article.summary || "Full text not available.";
    document.getElementById("modal-link").href = article.url;

    document.getElementById("modal").style.display = "block";
}

/* Modal close */
function closeModal() {
    document.getElementById("modal").style.display = "none";
}

/* Close modal if click outside */
window.onclick = function(event) {
    const modal = document.getElementById("modal");
    if (event.target === modal) {
        modal.style.display = "none";
    }
};
