document.getElementById("uploadForm").addEventListener("submit", async function(e) {
  e.preventDefault();
  const form = e.target;
  const formData = new FormData(form);

  const response = await fetch("/generate-gif", {
    method: "POST",
    body: formData,
  });

  const result = await response.json();
  document.getElementById("result").innerText = result.message || result.error;
});
