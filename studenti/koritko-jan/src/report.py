"""Z výsledků v results/ vyrobí:
  - tabulku výsledků v README.md (mezi značkami <!-- TABULKA -->),
  - results/chyby.md  – všechny chybné případy (podklad pro rozbor chyb),
  - results/cena.md   – odhad ceny 10 000 dotazů podle cen na OpenRouteru,
  - results/dashboard.html – vlastní dashboard s grafy (bonus).

    python src/report.py
Nevolá žádné API.
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
POLE = ["mesto", "teplota", "srazky", "typ_srazek"]

# Ceny placených (ne :free) variant na OpenRouteru v USD za 1 milion tokenů (vstup, výstup).
# Ověřeno na openrouter.ai 6. 11. 2026 – ceny se mění, před odevzdáním je zkontroluj.
CENY_OPENROUTER = {
    "openai/gpt-oss-20b": ("openai/gpt-oss-20b", 0.018, 0.09),
    "llama-3.3-70b-versatile": ("meta-llama/llama-3.3-70b-instruct", 0.10, 0.32),
    "mistral-small-latest": ("mistralai/mistral-small-3.2-24b-instruct", 0.075, 0.20),
    "llama-3.1-8b-instant": ("meta-llama/llama-3.1-8b-instruct", 0.02, 0.04),
    "openai/gpt-oss-120b": ("openai/gpt-oss-120b", 0.026, 0.095),
    "qwen/qwen3-32b": ("qwen/qwen3-32b", 0.08, 0.28),
}
USD_CZK = 23.0  # orientační kurz
DOTAZU = 10_000


def pct(x):
    return f"{x * 100:.0f} %"


def cz(x, des=2):
    return f"{x:,.{des}f}".replace(",", " ").replace(".", ",")


def nacti():
    s = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
    return s["behy"]


def tabulka(behy):
    radky = ["| Model | Poskytovatel | Prompt | Sada | Validní JSON | Úplná shoda | město | teplota | srážky | typ srážek "
             "| Latence | Tokeny (vstup/výstup) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for b in sorted(behy, key=lambda b: (b["sada"], b["prompt"], -b["uplna_shoda"])):
        p = b["pole"]
        radky.append(
            f"| {b['model']} | {b['poskytovatel']} | {b['prompt']} | {b['sada']} | {pct(b['validni_json'])} "
            f"| **{pct(b['uplna_shoda'])}** | {pct(p['mesto'])} | {pct(p['teplota'])} | {pct(p['srazky'])} "
            f"| {pct(p['typ_srazek'])} | {cz(b['latence_s'])} s | {cz(b['tokeny_vstup'], 0)} / {cz(b['tokeny_vystup'], 0)} |")
    return "\n".join(radky)


def vloz_do_readme(blok, znacka):
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    zac, kon = f"<!-- {znacka} START -->", f"<!-- {znacka} KONEC -->"
    if zac not in text:
        return
    pred, zbytek = text.split(zac, 1)
    _, po = zbytek.split(kon, 1)
    readme.write_text(f"{pred}{zac}\n{blok}\n{kon}{po}", encoding="utf-8")


def chyby():
    out = ["# Chybné případy\n", "Vygenerováno skriptem `src/report.py` ze surových výsledků v `results/`.\n"]
    for f in sorted(RES.glob("*_v*_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        s = d["souhrn"]
        spatne = [z for z in d["pripady"] if not z["vse"]]
        out.append(f"\n## {s['model']} ({s['poskytovatel']}), prompt {s['prompt']}, sada {s['sada']} – "
                   f"{len(spatne)} chyb z {s['pripadu']}\n")
        for z in spatne:
            pole = [p for p in POLE if not z["shody"][p]]
            out.append(f"- **#{z['id']}**{' (těžký)' if z['tezky'] else ''} – špatně: {', '.join(pole)}  \n"
                       f"  vstup: „{z['input']}“  \n"
                       f"  model: `{json.dumps(z['parsed'], ensure_ascii=False) if z['validni'] else (z['raw'] or '')[:200]}`  \n"
                       f"  správně: `{json.dumps(z['expected'], ensure_ascii=False)}`")
    (RES / "chyby.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def cena(behy):
    radky = [f"| Model (OpenRouter) | Prompt | Sada | Ø tokeny vstup / výstup na dotaz | Cena $/1M (vstup/výstup) "
             f"| {DOTAZU:,} dotazů USD | ≈ Kč |".replace(",", " "),
             "|---|---|---|---|---|---|---|"]
    for b in sorted(behy, key=lambda b: (b["sada"], b["prompt"], b["model"])):
        if b["model"] not in CENY_OPENROUTER or not b["pripadu"]:
            continue
        nazev, cin, cout = CENY_OPENROUTER[b["model"]]
        tin, tout = b["tokeny_vstup"] / b["pripadu"], b["tokeny_vystup"] / b["pripadu"]
        usd = DOTAZU * (tin * cin + tout * cout) / 1e6
        radky.append(f"| {nazev} | {b['prompt']} | {b['sada']} | {cz(tin, 0)} / {cz(tout, 0)} | {cin} / {cout} "
                     f"| {cz(usd, 3)} | {cz(usd * USD_CZK, 1)} |")
    blok = "\n".join(radky)
    (RES / "cena.md").write_text(
        f"# Odhad ceny {DOTAZU} dotazů\n\nCena = {DOTAZU} × (Ø vstupní tokeny × cena vstupu + Ø výstupní tokeny × "
        f"cena výstupu) / 1 000 000. Kurz {USD_CZK} Kč/USD.\n\n{blok}\n", encoding="utf-8")
    return blok


def dashboard(behy):
    data = json.dumps(behy, ensure_ascii=False)
    html = """<!doctype html><html lang="cs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Počasí – eval dashboard</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#f6f7f9;color:#1d2330}
h1{font-size:22px}h2{font-size:16px;margin:0 0 8px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}
.card{background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 3px #0001}
.row{display:flex;align-items:center;gap:8px;margin:4px 0;font-size:13px}
.lbl{width:190px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar{height:16px;border-radius:3px}.v{width:44px;text-align:right;font-variant-numeric:tabular-nums}
table{border-collapse:collapse;font-size:12px;width:100%}td,th{padding:4px 6px;border-bottom:1px solid #eee;text-align:left}
</style></head><body>
<h1>Zprávy o počasí – výsledky evalu (Jan Koritko)</h1>
<div class="grid" id="g"></div>
<div class="card" style="margin-top:16px"><h2>Všechny běhy</h2><table id="t"></table></div>
<script>
const B=__DATA__;
const C={v1:'#4f7fd9',v2:'#e08a2e',dev:'#4f7fd9',test:'#2ea86b'};
const pct=x=>Math.round(x*100)+' %';
function card(title,rows){const d=document.createElement('div');d.className='card';
 d.innerHTML='<h2>'+title+'</h2>'+rows.map(r=>'<div class="row"><span class="lbl" title="'+r[0]+'">'+r[0]+
 '</span><span style="flex:1;background:#eef0f4;border-radius:3px"><div class="bar" style="width:'+(r[1]*100)+
 '%;background:'+r[2]+'"></div></span><span class="v">'+pct(r[1])+'</span></div>').join('');
 document.getElementById('g').appendChild(d);}
const dv1=B.filter(b=>b.sada==='dev'&&b.prompt==='v1');
card('Porovnání modelů (dev, v1) – úplná shoda',dv1.map(b=>[b.model,b.uplna_shoda,C.v1]));
const models=[...new Set(B.filter(b=>b.sada==='dev').map(b=>b.model))];
card('v1 proti v2 (dev) – úplná shoda',models.flatMap(m=>['v1','v2'].map(p=>{
 const b=B.find(x=>x.sada==='dev'&&x.model===m&&x.prompt===p);return b?[m+' · '+p,b.uplna_shoda,C[p]]:null}).filter(Boolean)));
const tst=B.filter(b=>b.sada==='test');
card('dev proti test – úplná shoda',tst.flatMap(t=>{const d=B.find(x=>x.sada==='dev'&&x.model===t.model&&x.prompt===t.prompt);
 return [[t.model+' · '+t.prompt+' · dev',d?d.uplna_shoda:0,C.dev],[t.model+' · '+t.prompt+' · test',t.uplna_shoda,C.test]]}));
const fields=Object.keys((B[0]||{pole:{}}).pole);
const best=[...B].filter(b=>b.sada==='dev').sort((a,b)=>b.uplna_shoda-a.uplna_shoda)[0];
if(best)card('Přesnost po polích – '+best.model+' · '+best.prompt+' (dev)',fields.map(f=>[f,best.pole[f],'#8a5cd6']));
document.getElementById('t').innerHTML='<tr><th>model</th><th>posk.</th><th>prompt</th><th>sada</th><th>valid</th><th>shoda</th>'+
 fields.map(f=>'<th>'+f+'</th>').join('')+'<th>latence</th><th>tokeny</th></tr>'+B.map(b=>'<tr><td>'+b.model+'</td><td>'+
 b.poskytovatel+'</td><td>'+b.prompt+'</td><td>'+b.sada+'</td><td>'+pct(b.validni_json)+'</td><td><b>'+pct(b.uplna_shoda)+
 '</b></td>'+fields.map(f=>'<td>'+pct(b.pole[f])+'</td>').join('')+'<td>'+b.latence_s.toFixed(2)+' s</td><td>'+
 b.tokeny_vstup+' / '+b.tokeny_vystup+'</td></tr>').join('');
</script></body></html>"""
    (RES / "dashboard.html").write_text(html.replace("__DATA__", data), encoding="utf-8")


# ---------------------------------------------------------------- Fáze 5: rozbor z výsledků

# Co je na kterém případu záludné (napsáno při tvorbě sady, slouží k vysvětlení chyb).
ZALUDNOST = {
    3: "ráno mlha, přes den slunečno – slunečno znamená bez srážek",
    4: "záporná teplota se znakem − (unicode minus)",
    6: "teplota je napsaná slovem („patnácti“)",
    7: "teplota v textu vůbec není, správně je null",
    8: "text bez diakritiky a se zkratkou „C“",
    9: "rozpětí min/max – podle pravidel se bere nejvyšší hodnota",
    10: "dlouhý hovorový text, údaje jsou rozházené",
    11: "ironie – slova „krásné letní počasí“ tvrdí opak skutečnosti",
    12: "záporná teplota slovy („minus osm“)",
    13: "o srážkách text nic neříká, správně je null",
    14: "dvě města, počasí je popsané u prvního",
    15: "„přeháňky“ je déšť",
    16: "místo není město, ale hora",
    18: "ranní a odpolední teplota – bere se vyšší",
    19: "teplota ve °F, je potřeba přepočet (41 °F = 5 °C)",
    20: "text není zpráva o počasí, správně je všude null",
    21: "krupobití je samostatná kategorie",
    22: "překlepy, číslovka slovy a nejistá předpověď („možná sprchne“)",
    23: "„kolem nuly“ = 0 a déšť přecházející ve sníh",
    24: "rozpětí 17 až 19 °C – bere se 19",
    25: "mlha není srážka a zmínka o druhém městě",
}
POPIS_POLE = {"mesto": "město", "teplota": "teplota", "srazky": "srážky", "typ_srazek": "typ srážek"}


def proc_chyba(z, prompt):
    """Odhad příčiny chyby z toho, co model vrátil a co je na případu záludné."""
    if not z["validni"]:
        return ("Model nevrátil validní JSON (přidal text okolo nebo odpověď useknul). Je to chyba modelu – "
                "pomohl by `response_format: json_object` nebo přísnější instrukce v promptu.")
    e, o = z["expected"], z["parsed"] or {}
    duvody = []
    for p in POLE:
        if z["shody"][p]:
            continue
        ev, ov = e.get(p), o.get(p)
        if p == "mesto" and ev and isinstance(ov, str):
            duvody.append(f"město vrátil jako „{ov}“ místo „{ev}“ – buď jiný pád/tvar, nebo vybral jiné místo")
        elif ev is None and ov is not None:
            duvody.append(f"u pole {POPIS_POLE[p]} si údaj domyslel ({json.dumps(ov, ensure_ascii=False)}), "
                          "i když v textu není – modely nerady vracejí null")
        elif ev is not None and ov is None:
            duvody.append(f"pole {POPIS_POLE[p]} nechal prázdné, i když údaj v textu je")
        else:
            duvody.append(f"{POPIS_POLE[p]}: vrátil {json.dumps(ov, ensure_ascii=False)}, správně je "
                          f"{json.dumps(ev, ensure_ascii=False)}")
    zal = ZALUDNOST.get(z["id"])
    text = "; ".join(duvody) + "."
    if zal:
        text += f" Na případu je záludné: {zal}."
    if prompt == "v1" and zal and any(k in zal for k in ("bere se", "null", "kategorie", "přepočet", "znamená")):
        text += (" Prompt v1 tohle pravidlo vůbec neříká, takže jde spíš o **nejasné zadání** než o chybu modelu "
                 "(v2 pravidlo obsahuje).")
    else:
        text += " Pravidlo je v zadání jasné, jde spíš o **chybu modelu**."
    return text


def vyber_chyby(n=3):
    """Vybere n různých chybných případů, přednostně z dev v1 a s chybou v různých polích."""
    kandidati = []
    for f in sorted(RES.glob("*_v*_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        s = d["souhrn"]
        for z in d["pripady"]:
            if not z["vse"]:
                kandidati.append((s["sada"] != "dev", s["prompt"] != "v1", z["id"], s, z))
    kandidati.sort(key=lambda k: k[:3])
    vybrane, ids, pole_videna = [], set(), set()
    for _, _, i, s, z in kandidati:  # nejdřív různá pole
        spatne = frozenset(p for p in POLE if not z["shody"][p]) if z["validni"] else frozenset({"json"})
        if i not in ids and not spatne <= pole_videna:
            vybrane.append((s, z)); ids.add(i); pole_videna |= spatne
        if len(vybrane) == n:
            return vybrane
    for _, _, i, s, z in kandidati:
        if i not in ids:
            vybrane.append((s, z)); ids.add(i)
        if len(vybrane) == n:
            break
    return vybrane


def rozbor():
    vyb = vyber_chyby()
    if not vyb:
        return "Žádný model neudělal ani jednu chybu – sada je na tyhle modely asi moc lehká."
    out = []
    for k, (s, z) in enumerate(vyb, 1):
        vrat = json.dumps(z["parsed"], ensure_ascii=False) if z["validni"] else (z["raw"] or "")[:200]
        out.append(f"**{k}. Případ #{z['id']}** ({s['model']}, prompt {s['prompt']}, sada {s['sada']})\n\n"
                   f"- Vstup: „{z['input']}“\n- Model vrátil: `{vrat}`\n"
                   f"- Správně: `{json.dumps(z['expected'], ensure_ascii=False)}`\n"
                   f"- Proč: {proc_chyba(z, s['prompt'])}\n")
    return "\n".join(out)


def cena_10k(b):
    if b["model"] not in CENY_OPENROUTER or not b["pripadu"]:
        return None
    _, cin, cout = CENY_OPENROUTER[b["model"]]
    return DOTAZU * (b["tokeny_vstup"] / b["pripadu"] * cin + b["tokeny_vystup"] / b["pripadu"] * cout) / 1e6


def doporuceni(behy):
    dev = [b for b in behy if b["sada"] == "dev"]
    if not dev:
        return "Zatím žádný běh na dev sadě."
    best = sorted(dev, key=lambda b: (-b["uplna_shoda"], cena_10k(b) or 9e9, b["latence_s"]))[0]
    test = next((b for b in behy if b["sada"] == "test" and b["model"] == best["model"]
                 and b["prompt"] == best["prompt"]), None)
    usd = cena_10k(best)
    t = (f"Vybral bych **{best['model']}** ({best['poskytovatel']}) s promptem **{best['prompt']}**. Na dev sadě má "
         f"nejvyšší úplnou shodu ({pct(best['uplna_shoda'])}, validní JSON {pct(best['validni_json'])})")
    if test:
        t += f" a na test sadě {pct(test['uplna_shoda'])}"
    t += f", průměrná latence {cz(best['latence_s'])} s."
    if usd is not None:
        t += (f" Při naměřené spotřebě {cz(best['tokeny_vstup'] / best['pripadu'], 0)} vstupních a "
              f"{cz(best['tokeny_vystup'] / best['pripadu'], 0)} výstupních tokenů na dotaz by 10 000 dotazů denně "
              f"stálo na OpenRouteru asi **{cz(usd, 2)} USD (≈ {cz(usd * USD_CZK, 0)} Kč) denně**, "
              f"tj. ≈ {cz(usd * USD_CZK * 30, 0)} Kč měsíčně.")
    levnejsi = [b for b in dev if b is not best and cena_10k(b) is not None and usd is not None
                and cena_10k(b) < usd and b["uplna_shoda"] >= best["uplna_shoda"] - 0.07]
    if levnejsi:
        l = min(levnejsi, key=cena_10k)
        t += (f" Levnější alternativa s podobnou přesností je {l['model']} + {l['prompt']} "
              f"({pct(l['uplna_shoda'])}, ≈ {cz(cena_10k(l) * USD_CZK, 0)} Kč za 10 000 dotazů).")
    v1 = {b["model"]: b for b in dev if b["prompt"] == "v1"}
    v2 = {b["model"]: b for b in dev if b["prompt"] == "v2"}
    spol = [m for m in v1 if m in v2]
    if spol:
        rozdil = sum(v2[m]["uplna_shoda"] - v1[m]["uplna_shoda"] for m in spol) / len(spol)
        pomer = sum(v2[m]["tokeny_vstup"] for m in spol) / max(1, sum(v1[m]["tokeny_vstup"] for m in spol))
        t += (f" Prompt v2 změnil úplnou shodu v průměru o {rozdil * 100:+.0f} procentních bodů, ale má "
              f"{cz(pomer, 1)}× víc vstupních tokenů – u takhle levných modelů je to pořád zanedbatelná cena, "
              f"rozhoduje hlavně přesnost.")
    return t


def dev_test(behy):
    radky, rozdily = [], []
    for t in [b for b in behy if b["sada"] == "test"]:
        d = next((b for b in behy if b["sada"] == "dev" and b["model"] == t["model"] and b["prompt"] == t["prompt"]), None)
        if d:
            rozdily.append(t["uplna_shoda"] - d["uplna_shoda"])
            radky.append(f"- {t['model']} + {t['prompt']}: dev {pct(d['uplna_shoda'])} → test {pct(t['uplna_shoda'])} "
                         f"({(t['uplna_shoda'] - d['uplna_shoda']) * 100:+.0f} p. b.)")
    if not radky:
        return "Na test sadě zatím nic neběželo."
    if all(abs(r) < 1e-9 for r in rozdily):
        zaver = ("Výsledky na dev a test se neliší. Prompt v2 jsem psal podle pravidel ze schématu (ne podle konkrétních "
                 "případů z test sady) a ověřoval jen na dev sadě. Pravidla v něm jsou obecná (pád města, rozpětí teplot, null, °F) a few-shot příklady nejsou z žádné sady, takže se "
                 "nepřeučil na konkrétní případy – fungoval i na test sadě, která má záludnosti, jaké v dev nejsou "
                 "(°F, text, který není o počasí, krupobití). Na druhou stranu 10 případů je málo (1 případ = 10 p. b.) "
                 "a stoprocentní výsledek spíš ukazuje, že je sada pro tyhle modely už lehká; pro přesnější srovnání "
                 "by byla potřeba větší a těžší sada.")
    elif sum(rozdily) < 0:
        zaver = ("Na test sadě je výsledek horší. Prompt v2 jsem ladil podle chyb na dev sadě, takže se na ní dá čekat "
                 "lepší výsledek (mírné přeučení), a test sada má záludnosti, které v dev nejsou (°F, text, který není "
                 "o počasí, krupobití). Test má navíc jen 10 případů, takže jeden případ = 10 procentních bodů.")
    else:
        zaver = ("Na test sadě je výsledek dokonce lepší – při 10 případech (1 případ = 10 p. b.) je to spíš náhoda "
                 "a rozdílná obtížnost případů než skutečné zlepšení.")
    return "\n".join(radky) + "\n\n" + zaver


VELIKOST = {"openai/gpt-oss-20b": "~20 mld. parametrů", "llama-3.3-70b-versatile": "70 mld.",
            "mistral-small-latest": "~24 mld.", "llama-3.1-8b-instant": "8 mld.", "openai/gpt-oss-120b": "~120 mld.",
            "gemini-flash-latest": "velikost nezveřejněna", "qwen/qwen3-32b": "32 mld.", "allam-2-7b": "7 mld."}


def pouzite_modely(behy):
    m = dict.fromkeys((b["model"], b["poskytovatel"]) for b in behy)
    return "Použité modely: " + ", ".join(f"`{mo}` ({po}, {VELIKOST.get(mo, '?')})" for mo, po in m) + "."


def main():
    if not (RES / "summary.json").exists():
        sys.exit("results/summary.json zatím neexistuje – nejdřív spusť eval.")
    behy = nacti()
    vloz_do_readme(tabulka(behy), "TABULKA")
    vloz_do_readme(cena(behy), "CENA")
    vloz_do_readme(pouzite_modely(behy), "MODELY")
    vloz_do_readme(rozbor(), "ROZBOR")  # jen když v README značky ROZBOR zůstaly
    vloz_do_readme(doporuceni(behy), "DOPORUCENI")
    vloz_do_readme(dev_test(behy), "DEVTEST")
    chyby()
    dashboard(behy)
    print("Report hotový: tabulka v README.md, results/chyby.md, results/cena.md, results/dashboard.html")


if __name__ == "__main__":
    main()
