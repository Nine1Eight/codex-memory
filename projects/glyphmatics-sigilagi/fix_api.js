async function runSigil() {

    const input = document.getElementById("inputBox").value;
    setStatus("calling /api/predict...");

    try {
        const res = await fetch(
            "https://nine1eight-vil-glyphmatic-demo.hf.space/api/predict",
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    data: [input, "web"]
                })
            }
        );

        if (!res.ok) throw new Error("HTTP " + res.status);

        const json = await res.json();

        console.log("RAW:", json);

        const data = json.data;

        document.getElementById("response").innerText = data[0];
        document.getElementById("lattice").innerText = data[1];
        document.getElementById("inspect").innerText = data[2];

        renderGlyphs(data[1]);

        setStatus("success");

    } catch (err) {
        console.error(err);
        setStatus("ERROR: " + err.message);
        document.getElementById("response").innerText = "API FAILED";
    }
}
