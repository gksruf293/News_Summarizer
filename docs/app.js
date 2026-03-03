fetch("../data/todays_news.json")
    .then(response => response.json())
    .then(data => {
        document.getElementById("date").innerText =
            "Date: " + data.date;

        const container = document.getElementById("news-container");

        data.articles.forEach(article => {
            const div = document.createElement("div");
            div.className = "article";

            div.innerHTML = `
                <h2>${article.title}</h2>
                <a href="${article.url}" target="_blank">Read original</a>
                <p>${article.summary}</p>
                <hr>
            `;

            container.appendChild(div);
        });
    });
