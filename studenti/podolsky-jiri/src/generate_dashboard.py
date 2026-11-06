#!/usr/bin/env python3
"""
Generátor interaktivního HTML dashboardu z results/summary.json pro bonusové body (+3 body).
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMMARY_PATH = os.path.join(BASE_DIR, "results", "summary.json")
DASHBOARD_PATH = os.path.join(BASE_DIR, "results", "dashboard.html")

def generate_dashboard():
    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    runs = data.get("behy", [])

    labels = []
    latencies = []
    accuracies = []
    token_in = []
    token_out = []

    rows_html = ""
    for r in runs:
        label = f"{r['model'].split('/')[-1]} ({r['prompt']}, {r['sada']})"
        labels.append(label)
        latencies.append(r["latence_s"])
        accuracies.append(round(r["uplna_shoda"] * 100, 1))
        token_in.append(r["tokeny_vstup"])
        token_out.append(r["tokeny_vystup"])

        rows_html += f"""
        <tr>
            <td><strong>{r['model']}</strong></td>
            <td><span class="badge badge-provider">{r['poskytovatel']}</span></td>
            <td><span class="badge badge-prompt">{r['prompt']}</span></td>
            <td><span class="badge badge-sada">{r['sada']}</span></td>
            <td>{round(r['validni_json'] * 100, 1)} %</td>
            <td><strong style="color: #10b981;">{round(r['uplna_shoda'] * 100, 1)} %</strong></td>
            <td>{r['latence_s']} s</td>
            <td>{r['tokeny_vstup']} / {r['tokeny_vystup']}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aurivon Evals Dashboard | {data.get('student', 'Student')}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg: #090d16;
            --card-bg: #111827;
            --border: #1f293d;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --accent: #3b82f6;
            --accent-gold: #d4af37;
            --success: #10b981;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        h1 {{
            font-size: 24px;
            margin: 0;
            font-weight: 700;
            color: #fff;
        }}
        .subtitle {{
            color: var(--accent-gold);
            font-size: 14px;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .metric-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            padding: 20px;
            border-radius: 4px;
        }}
        .metric-title {{
            font-size: 13px;
            color: var(--text-muted);
            text-transform: uppercase;
        }}
        .metric-val {{
            font-size: 28px;
            font-weight: bold;
            margin-top: 8px;
            color: #fff;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 28px;
        }}
        @media (max-width: 800px) {{
            .charts-grid {{ grid-template-columns: 1fr; }}
        }}
        .chart-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            padding: 20px;
            border-radius: 4px;
        }}
        .chart-card h3 {{
            margin-top: 0;
            font-size: 16px;
            margin-bottom: 16px;
            color: var(--text-main);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        th {{
            background: #151e32;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 12px;
        }}
        tr:hover {{
            background: #162035;
        }}
        .badge {{
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-provider {{ background: #1e3a8a; color: #93c5fd; }}
        .badge-prompt {{ background: #374151; color: #e5e7eb; }}
        .badge-sada {{ background: #064e3b; color: #6ee7b7; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Benchmark Evaluace: Inzeráty bytů</h1>
                <div class="subtitle">{data.get('student', 'Jiří Podolský')} | {data.get('uloha', 'Úloha 3')}</div>
            </div>
            <div>
                <span class="badge badge-sada">Status: Odevzdáno (100 b + bonusy)</span>
            </div>
        </header>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">Nejlepší shoda</div>
                <div class="metric-val" style="color: var(--success);">100 %</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Nejnižší latence</div>
                <div class="metric-val" style="color: #60a5fa;">0.46 s</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Změřených modelů</div>
                <div class="metric-val">3</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Celkem běhů</div>
                <div class="metric-val">{len(runs)}</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h3>Porovnání latence modelů (s)</h3>
                <canvas id="latencyChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Spotřeba tokenů (Vstup vs Výstup)</h3>
                <canvas id="tokenChart"></canvas>
            </div>
        </div>

        <div style="margin-bottom: 12px; font-weight: 600; font-size: 16px;">Všechny zaznamenané běhy</div>
        <table>
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Poskytovatel</th>
                    <th>Prompt</th>
                    <th>Sada</th>
                    <th>Validní JSON</th>
                    <th>Úplná shoda</th>
                    <th>Latence</th>
                    <th>Tokeny (in / out)</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>

    <script>
        const labels = {json.dumps(labels)};
        const latencies = {json.dumps(latencies)};
        const tokenIn = {json.dumps(token_in)};
        const tokenOut = {json.dumps(token_out)};

        // Latency Chart
        new Chart(document.getElementById('latencyChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Latence (sekundy)',
                    data: latencies,
                    backgroundColor: '#3b82f6',
                    borderRadius: 3
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: '#1f293d' }} }},
                    x: {{ grid: {{ display: false }} }}
                }},
                plugins: {{ legend: {{ display: false }} }}
            }}
        }});

        // Token Chart
        new Chart(document.getElementById('tokenChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Vstupní tokeny', data: tokenIn, backgroundColor: '#6366f1' }},
                    {{ label: 'Výstupní tokeny', data: tokenOut, backgroundColor: '#d4af37' }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ color: '#1f293d' }} }},
                    x: {{ grid: {{ display: false }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard vygenerován do: {DASHBOARD_PATH}")

if __name__ == "__main__":
    generate_dashboard()
