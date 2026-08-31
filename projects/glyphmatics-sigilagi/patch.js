async function runSigil() {

    const input = document.getElementById("inputBox").value;
    setStatus("calling backend...");

    try {

        const res = await fetch("https://nine1eight-vil-glyphmatic-demo.hf.space/run/predictive", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                user_input: input,
                session_id: "web"
            })
        });

        const json = await res.json();

        console.log("RAW:", json);

        // handle BOTH formats safely
        const data = Array.isArray(json) ? json : json.data;

        if (!data) throw new Error("No data returned");

        document.getElementById("response").innerText = data[0] || "no response";
        document.getElementById("lattice").innerText = data[1] || "no lattice";
        document.getElementById("inspect").innerText = data[2] || "no inspect";

        renderGlyphs(data[1]);

        setStatus("success");

    } catch (err) {
        console.error(err);
        setStatus("ERROR: " + err.message);
    }
}
