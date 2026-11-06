#!/usr/bin/env python3
"""
Generátor vlastního HTML dashboardu z results/summary.json.
Vytváří moderní, interaktivní přehled výsledků bez externích závislostí.
"""

import json
import os

def generate_dashboard():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    summary_path = os.path.join(base_dir, "results", "summary.json")

    if not os.path.exists(summary_path):
        print("Soubor summary.json nenalezen!")
        return

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    behy = data.get("behy", [])
    student = data.get("student", "Vilém Malý")
    uloha = data.get("uloha", "Hlášení závad v učebně")

    # Najdeme nejlepší běhy
    best_exact = max((b.get("uplna_shoda", 0) for b in behy), default=0)
    best_run = next((b for b in behy if b.get("uplna_shoda") == best_exact), None)

    rows_html = ""
    for b in behy:
        m = b.get("model", "")
        prov = b.get("poskytovatel", "")
        pr = b.get("prompt", "")
        sada = b.get("sada", "")
        val_json = b.get("validni_json", 0) * 100
        shoda = b.get("uplna_shoda", 0) * 100
        lat = b.get("latence_s", 0)
        tok_in = b.get("tokeny_vstup", 0)
        tok_out = b.get("tokeny_vystup", 0)
        pole = b.get("pole", {})
        kat = pole.get("kategorie", 0) * 100
        prio = pole.get("priorita", 0) * 100
        uceb = pole.get("ucebna", 0) * 100

        badge_class = "badge-success" if shoda >= 85 else ("badge-warning" if shoda >= 70 else "badge-danger")

        rows_html += f"""
        <tr>
          <td><strong>{m}</strong></td>
          <td><span class="provider-pill">{prov}</span></td>
          <td><code>{pr}</code></td>
          <td><span class="badge {'badge-dev' if sada=='dev' else 'badge-test'}">{sada}</span></td>
          <td>{val_json:.1f} %</td>
          <td><span class="badge {badge_class}">{shoda:.1f} %</span></td>
          <td>
            <div class="field-bar-wrap" title="kategorie: {kat:.0f}%, priorita: {prio:.0f}%, učebna: {uceb:.0f}%">
              <span class="field-badge">K: {kat:.0f}%</span>
              <span class="field-badge">P: {prio:.0f}%</span>
              <span class="field-badge">U: {uceb:.0f}%</span>
            </div>
          </td>
          <td>{lat:.2f} s</td>
          <td>{tok_in:,} / {tok_out:,}</td>
        </tr>
        """

    # Příprava dat pro grafy
    labels = [f"{b['model'].split('/')[-1]} ({b['prompt']}/{b['sada']})" for b in behy]
    shody = [b.get("uplna_shoda", 0) * 100 for b in behy]
    latence = [b.get("latence_s", 0) for b in behy]

    html_content = f"""<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard Evaluace - {uloha}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --success: #22c55e;
      --warning: #f59e0b;
      --danger: #ef4444;
      --card-hover: #243247;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 2rem;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1rem;
    }}
    h1 {{ font-size: 1.8rem; font-weight: 700; color: var(--primary); }}
    .subtitle {{ color: var(--text-muted); font-size: 0.95rem; }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem;
    }}
    .kpi-title {{ font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
    .kpi-value {{ font-size: 1.8rem; font-weight: 700; margin-top: 0.5rem; }}
    .kpi-sub {{ font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem; }}

    .charts-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin-bottom: 2rem;
    }}
    @media (max-width: 850px) {{
      .charts-grid {{ grid-template-columns: 1fr; }}
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.5rem;
    }}
    .card-title {{
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 1rem;
      color: var(--primary);
      display: flex;
      justify-content: space-between;
    }}
    .bar-row {{
      display: flex;
      align-items: center;
      margin-bottom: 0.75rem;
      font-size: 0.85rem;
    }}
    .bar-label {{ width: 220px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; }}
    .bar-track {{ flex: 1; height: 18px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; margin: 0 0.75rem; }}
    .bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.5s; }}
    .bar-fill-acc {{ background: linear-gradient(90deg, #0284c7, #38bdf8); }}
    .bar-fill-lat {{ background: linear-gradient(90deg, #f59e0b, #ef4444); }}
    .bar-val {{ width: 55px; text-align: right; font-weight: 600; }}

    table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.9rem;
    }}
    th, td {{
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--border);
    }}
    th {{
      background: rgba(255,255,255,0.02);
      color: var(--text-muted);
      font-weight: 600;
    }}
    tr:hover td {{ background: var(--card-hover); }}
    .badge {{
      display: inline-block;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      font-size: 0.8rem;
      font-weight: 600;
    }}
    .badge-success {{ background: rgba(34, 197, 94, 0.2); color: var(--success); border: 1px solid var(--success); }}
    .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }}
    .badge-danger {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }}
    .badge-dev {{ background: #1e3a5f; color: #60a5fa; }}
    .badge-test {{ background: #3b1d54; color: #c084fc; }}
    .provider-pill {{
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.05em;
      background: rgba(255,255,255,0.1);
      padding: 0.15rem 0.4rem;
      border-radius: 3px;
    }}
    .field-bar-wrap {{ display: flex; gap: 0.3rem; }}
    .field-badge {{
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--border);
      padding: 0.1rem 0.3rem;
      border-radius: 3px;
      font-size: 0.75rem;
    }}
    footer {{
      margin-top: 3rem;
      text-align: center;
      color: var(--text-muted);
      font-size: 0.85rem;
      border-top: 1px solid var(--border);
      padding-top: 1.5rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>Dashboard Evaluace LLM</h1>
        <div class="subtitle">{uloha} | Student: <strong>{student}</strong></div>
      </div>
      <div>
        <span class="badge badge-dev">Celkem běhů: {len(behy)}</span>
      </div>
    </header>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-title">Nejvyšší přesnost (Úplná shoda)</div>
        <div class="kpi-value" style="color: var(--success);">{best_exact * 100:.1f} %</div>
        <div class="kpi-sub">{best_run['model'] if best_run else ''} ({best_run['prompt'] if best_run else ''})</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Průměrná validita JSON</div>
        <div class="kpi-value" style="color: var(--primary);">{sum(b.get('validni_json', 0) for b in behy)/len(behy)*100 if behy else 0:.1f} %</div>
        <div class="kpi-sub">Strukturovaný výstup bez pádů</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Nejrychlejší model</div>
        <div class="kpi-value">{min((b.get('latence_s', 99) for b in behy), default=0):.2f} s</div>
        <div class="kpi-sub">Qwen 3.8-27B (Groq)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Zkoumané modely</div>
        <div class="kpi-value">{len(set(b['model'] for b in behy))}</div>
        <div class="kpi-sub">20B, 27B, 31B a 120B parametry</div>
      </div>
    </div>

    <div class="charts-grid">
      <div class="card">
        <div class="card-title">Porovnání přesnosti (Úplná shoda %)</div>
        <div id="chart-accuracy">
          {''.join(f'''
          <div class="bar-row">
            <span class="bar-label" title="{b['model']}">{b['model'].split('/')[-1]} [{b['prompt']}/{b['sada']}]</span>
            <div class="bar-track">
              <div class="bar-fill bar-fill-acc" style="width: {b.get('uplna_shoda', 0)*100}%;"></div>
            </div>
            <span class="bar-val">{b.get('uplna_shoda', 0)*100:.1f} %</span>
          </div>
          ''' for b in behy)}
        </div>
      </div>

      <div class="card">
        <div class="card-title">Průměrná latence odpovědi (sekundy)</div>
        <div id="chart-latency">
          {''.join(f'''
          <div class="bar-row">
            <span class="bar-label" title="{b['model']}">{b['model'].split('/')[-1]} [{b['poskytovatel']}]</span>
            <div class="bar-track">
              <div class="bar-fill bar-fill-lat" style="width: {min(100, (b.get('latence_s', 0)/7.5)*100)}%;"></div>
            </div>
            <span class="bar-val">{b.get('latence_s', 0):.2f} s</span>
          </div>
          ''' for b in behy)}
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Detailní přehled všech běhů</div>
      <div style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Poskytovatel</th>
              <th>Prompt</th>
              <th>Sada</th>
              <th>Validní JSON</th>
              <th>Úplná shoda</th>
              <th>Přesnost po polích (K / P / U)</th>
              <th>Latence</th>
              <th>Tokeny (vstup/výstup)</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </div>
    </div>

    <footer>
      Generováno automaticky skriptem <code>src/generate_dashboard.py</code> z výsledků evaluace.
    </footer>
  </div>
</body>
</html>
"""

    dashboard_path = os.path.join(base_dir, "results", "dashboard.html")
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"HTML Dashboard vygenerován do: {dashboard_path}")

if __name__ == "__main__":
    generate_dashboard()

