document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const resultDiv = document.getElementById("result");
    const progressDiv = document.getElementById("progress");

    resultDiv.innerHTML = "";
    progressDiv.innerText = "Uploading and processing...";

    const res = await fetch("/generate", {
        method: "POST",
        body: formData
    });
    const data = await res.json();
    if (!data.job_id) {
        resultDiv.innerText = "Error: " + (data.error || "Unknown error");
        return;
    }

    const job_id = data.job_id;

    const interval = setInterval(async () => {
        const progRes = await fetch(`/progress/${job_id}`);
        const progData = await progRes.json();

        if (progData.error) {
            clearInterval(interval);
            resultDiv.innerText = "Error: " + progData.error;
            return;
        }

        progressDiv.innerText = `Status: ${progData.stage} (${Math.floor(progData.progress)}%)`;

        if (progData.stage === "complete") {
            clearInterval(interval);
            progressDiv.innerText = "✅ GIFs generated successfully!";

            progData.gifs.forEach(gif => {
                const container = document.createElement("div");
                const img = document.createElement("img");
                img.src = gif;
                img.style = "max-width: 300px; display: block; margin-bottom: 10px;";
                const download = document.createElement("a");
                download.href = gif;
                download.innerText = "⬇️ Download";
                download.download = gif.split("/").pop();
                container.appendChild(img);
                container.appendChild(download);
                resultDiv.appendChild(container);
            });
        }
    }, 1000);
});
