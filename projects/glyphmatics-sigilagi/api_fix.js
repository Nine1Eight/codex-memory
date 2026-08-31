async function runSigil() {

    const input = document.getElementById("inputBox").value;
    setStatus("calling backend...");

    try {
        const res = await fetch(
            "https://nine1eight-vil-glyphmatic-demo.hf.space/api/predict",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    data: [input, "web-session"]
                })
            }
        );

        if (!res.ok) throw new Error("HTTP " + res.status);

        const json = await res.json();

        console.log("API RESPONSE:", json);

        const [response, lattice, inspect] = json.data;

        document.getElementById("responseBox").innerText = response;
        document.getElementById("glyphBox").innerText = lattice;
        document.getElementById("inspectBox").innerText = inspect;

        renderGlyphs(lattice);

        setStatus("success");

    } catch (err) {
        console.error(err);
        setStatus("ERROR: " + err.message);
    }
}
