let newsData = null;

fetch("../data/todays_news.json")
    .then(response => response.json())
    .then(data => {
        newsData = data;
        renderAllCategories();
    });

function renderAllCategories() {
    const container = document.getElementById("news-container");
    container.innerHTML = "";

    for (const category in newsData.categories) {
        renderCategory(category, newsData.categories[category]);
    }
}

function renderCategory(category, articles) {
    const container = document.getElementById("news-container");

    const section = document.createElement("div");
    section.className = "category-section";

    section.innerHTML = `
        <h2>📌 ${category.toUpperCase()}</h2>
    `;

    articles.forEach(article => {
        const div = document.createElement("div");
        div.className = "article";

        div.innerHTML = `
            <h3>${article.title}</h3>
            <a href="${article.url}" target="_blank">Read original</a>
            <p>${article.summary}</p>
            <hr>
        `;

        section.appendChild(div);
    });

    container.appendChild(section);
}

function filterByCategory(category) {
    const container = document.getElementById("news-container");
    container.innerHTML = "";
    renderCategory(category, newsData.categories[category]);
}

function handleSearch() {
    const interest = document.getElementById("interestInput").value;
    alert("Interest search will be implemented next: " + interest);
}
