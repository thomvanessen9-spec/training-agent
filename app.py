from flask import Flask, request, jsonify, send_from_directory
import anthropic
import json
from datetime import date
import os

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
DATA_FILE = "logboek.json"

def laad_logboek():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"workouts": [], "maaltijden": []}

def sla_logboek_op(logboek):
    with open(DATA_FILE, "w") as f:
        json.dump(logboek, f, ensure_ascii=False, indent=2)

logboek = laad_logboek()

TOOLS = [
    {
        "name": "log_workout",
        "description": "Sla een training op. Gebruik dit als de gebruiker een workout beschrijft.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Type training, bijv. 'Hyrox', 'Krachttraining', 'Spinning'"},
                "duur_minuten": {"type": "integer", "description": "Duur in minuten"},
                "oefeningen": {"type": "string", "description": "Omschrijving van oefeningen"},
                "calories_verbrand": {"type": "integer", "description": "Geschatte calorieën verbrand"},
                "intensiteit": {"type": "string", "description": "Intensiteit: 'laag', 'middel', 'hoog'"},
                "gewichten": {"type": "string", "description": "Gebruikte gewichten, bijv. 'squat 100kg, deadlift 140kg'"},
                "notities": {"type": "string", "description": "Extra notities over de workout"}
            },
            "required": ["type", "duur_minuten"]
        }
    },
    {
        "name": "log_maaltijd",
        "description": "Sla een maaltijd op. Gebruik dit als de gebruiker beschrijft wat hij gegeten heeft.",
        "input_schema": {
            "type": "object",
            "properties": {
                "naam": {"type": "string", "description": "Naam van de maaltijd"},
                "calories": {"type": "integer", "description": "Aantal calorieen"},
                "eiwitten_g": {"type": "integer", "description": "Gram eiwit"},
                "koolhydraten_g": {"type": "integer", "description": "Gram koolhydraten"},
                "vetten_g": {"type": "integer", "description": "Gram vet"},
                "vezels_g": {"type": "integer", "description": "Gram vezels"},
                "tijd": {"type": "string", "description": "Tijdstip, bijv. 'ontbijt', 'lunch', 'avondeten', 'snack'"}
            },
            "required": ["naam", "calories", "eiwitten_g"]
        }
    },
    {
        "name": "haal_dagoverzicht",
        "description": "Geef een overzicht van alle workouts en maaltijden van vandaag.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "verwijder_entry",
        "description": "Verwijder een gelogde workout of maaltijd.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Wat te verwijderen: 'workout' of 'maaltijd'"},
                "index": {"type": "integer", "description": "Het nummer van de entry (0 = eerste, 1 = tweede, etc.)"}
            },
            "required": ["type", "index"]
        }
    }
]

def log_workout(type, duur_minuten, oefeningen="", calories_verbrand=0, intensiteit="", gewichten="", notities=""):
    entry = {
        "datum": str(date.today()),
        "type": type,
        "duur_minuten": duur_minuten,
        "oefeningen": oefeningen,
        "calories_verbrand": calories_verbrand,
        "intensiteit": intensiteit,
        "gewichten": gewichten,
        "notities": notities
    }
    logboek["workouts"].append(entry)
    sla_logboek_op(logboek)
    return f"Workout gelogd: {type}, {duur_minuten} minuten."

def log_maaltijd(naam, calories, eiwitten_g, koolhydraten_g=0, vetten_g=0, vezels_g=0, tijd=""):
    entry = {
        "datum": str(date.today()),
        "naam": naam,
        "calories": calories,
        "eiwitten_g": eiwitten_g,
        "koolhydraten_g": koolhydraten_g,
        "vetten_g": vetten_g,
        "vezels_g": vezels_g,
        "tijd": tijd
    }
    logboek["maaltijden"].append(entry)
    sla_logboek_op(logboek)
    return f"Maaltijd gelogd: {naam}, {calories} kcal, {eiwitten_g}g eiwit."

def haal_dagoverzicht():
    vandaag = str(date.today())
    workouts_vandaag = [w for w in logboek["workouts"] if w["datum"] == vandaag]
    maaltijden_vandaag = [m for m in logboek["maaltijden"] if m["datum"] == vandaag]
    totaal_kcal = sum(m["calories"] for m in maaltijden_vandaag)
    totaal_eiwit = sum(m["eiwitten_g"] for m in maaltijden_vandaag)
    totaal_carbs = sum(m["koolhydraten_g"] for m in maaltijden_vandaag)
    totaal_vet = sum(m["vetten_g"] for m in maaltijden_vandaag)
    totaal_vezels = sum(m["vezels_g"] for m in maaltijden_vandaag)
    totaal_verbrand = sum(w.get("calories_verbrand", 0) for w in workouts_vandaag)
    return json.dumps({
        "workouts": workouts_vandaag,
        "maaltijden": maaltijden_vandaag,
        "totaal_calories": totaal_kcal,
        "totaal_eiwit_g": totaal_eiwit,
        "totaal_koolhydraten_g": totaal_carbs,
        "totaal_vetten_g": totaal_vet,
        "totaal_vezels_g": totaal_vezels,
        "totaal_verbrand": totaal_verbrand
    }, ensure_ascii=False)

def verwijder_entry(type, index):
    vandaag = str(date.today())
    if type == "workout":
        entries = [w for w in logboek["workouts"] if w["datum"] == vandaag]
        if index < 0 or index >= len(entries):
            return f"Geen workout gevonden op positie {index}."
        te_verwijderen = entries[index]
        logboek["workouts"].remove(te_verwijderen)
        sla_logboek_op(logboek)
        return f"Workout verwijderd: {te_verwijderen['type']}."
    elif type == "maaltijd":
        entries = [m for m in logboek["maaltijden"] if m["datum"] == vandaag]
        if index < 0 or index >= len(entries):
            return f"Geen maaltijd gevonden op positie {index}."
        te_verwijderen = entries[index]
        logboek["maaltijden"].remove(te_verwijderen)
        sla_logboek_op(logboek)
        return f"Maaltijd verwijderd: {te_verwijderen['naam']}."
    return "Type moet 'workout' of 'maaltijd' zijn."

def voer_tool_uit(tool_naam, tool_input):
    if tool_naam == "log_workout":
        return log_workout(**tool_input)
    elif tool_naam == "log_maaltijd":
        return log_maaltijd(**tool_input)
    elif tool_naam == "haal_dagoverzicht":
        return haal_dagoverzicht()
    elif tool_naam == "verwijder_entry":
        return verwijder_entry(**tool_input)
    return f"Onbekende tool: {tool_naam}"

geschiedenis = []

@app.route("/logboek")
def get_logboek():
    return jsonify({"logboek": logboek})
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    gebruikersbericht = data.get("bericht")
    geschiedenis.append({"role": "user", "content": gebruikersbericht})

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system="""Je bent een persoonlijke fitness en voedingsassistent voor Thom.
            Thom traint serieus: Hyrox, krachttraining, spinning en cardio.
            Hij tracked zijn macro's nauwkeurig met focus op hoog eiwitinname.
            Basisdoel per dag: 2000 kcal + calorieën verbrand door sport. 180g eiwit, 60g vet, 300g koolhydraten, 30g vezels.
            Wees direct en informeel. Geen onnodige disclaimers. Log altijd automatisch 
            als de gebruiker een training of maaltijd beschrijft. Schat ontbrekende 
            macros in op basis van je kennis als dat nodig is.""",
            messages=geschiedenis,
            tools=TOOLS
        )

        geschiedenis.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for blok in response.content:
                if hasattr(blok, "text"):
                    return jsonify({"antwoord": blok.text, "logboek": logboek})

        tool_resultaten = []
        for blok in response.content:
            if blok.type == "tool_use":
                resultaat = voer_tool_uit(blok.name, blok.input)
                tool_resultaten.append({"type": "tool_result", "tool_use_id": blok.id, "content": str(resultaat)})

        geschiedenis.append({"role": "user", "content": tool_resultaten})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
app.run(debug=False, host="0.0.0.0", port=port)