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


def main():
    if not (RES / "summary.json").exists():
        sys.exit("results/summary.json zatím neexistuje – nejdřív spusť eval.")
    behy = nacti()
    vloz_do_readme(tabulka(behy), "TABULKA")
    vloz_do_readme(cena(behy), "CENA")
    chyby()
    dashboard(behy)
    print("Report hotový: tabulka v README.md, results/chyby.md, results/cena.md, results/dashboard.html")


if __name__ == "__main__":
    main()
