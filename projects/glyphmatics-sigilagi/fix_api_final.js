async function runSigil() {

    const input = document.getElementById("inputBox").value;
    setStatus("probing API...");

    const endpoints = [
        "/run/run_predictive",
        "/api/predict",
        "/run/predict"
    ];

    for (let ep of endpoints) {
        try {
            const url = "https://nine1eight-vil-glyphmatic-demo.hf.space" + ep;

            const res = await fetch(url, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    data: [input, "web"],
                    user_input: input,
                    session_id: "web"
                })
            });

            if (!res.ok) throw new Error("HTTP " + res.status);

            const json = await res.json();
            console.log("SUCCESS endpoint:", ep, json);

            const data = json.data || json;

            updateUI(data);
            setStatus("success → " + ep);
            return;

        } catch (e) {
            console.warn("failed:", ep);
        }
    }

    setStatus("ALL ENDPOINTS FAILED");
}
