"""
verification/dashboard.py
-------------------------
Compiles the verification results and plots into an interactive single-page HTML dashboard.
"""

import os
import json
import time
import platform
import sys

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "verification_results.json")
DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), "dashboard.html")


def compile_dashboard() -> None:
    # 1. Load verification results
    if not os.path.exists(RESULTS_PATH):
        print("Cannot build dashboard — verification_results.json not found.")
        return

    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        results = json.load(f)

    # Load Kurla study results
    kurla_summary_path = os.path.join(OUTPUTS_DIR, "kurla_summary.json")
    kurla_summary = {}
    if os.path.exists(kurla_summary_path):
        with open(kurla_summary_path, "r", encoding="utf-8") as f:
            kurla_summary = json.load(f)

    # System profile
    sys_profile = {
        "os": platform.platform(),
        "python_ver": sys.version.split()[0],
        "processor": platform.processor() or "unknown",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    # Build HTML sections
    benchmark_cards = ""
    for name, data in results.items():
        status = data.get("status", "UNKNOWN")
        status_color = "rgba(16, 185, 129, 0.2)" if status in ("PASS", "GOLDEN") else "rgba(239, 68, 68, 0.2)"
        status_text_color = "#10b981" if status in ("PASS", "GOLDEN") else "#ef4444"
        
        # Image links (relative paths)
        hist_url = f"plots/{name}/water_depth_histogram.png"
        hydro_url = f"plots/{name}/hydrograph.png"
        mass_url = f"plots/{name}/mass_balance.png"
        area_url = f"plots/{name}/flooded_area_vs_time.png"
        drain_url = f"plots/{name}/drain_utilization.png"
        outfall_url = f"plots/{name}/outfall_utilization.png"

        benchmark_cards += f"""
        <div class="card">
            <div class="card-header">
                <h3>Benchmark: {name.replace('_', ' ').title()}</h3>
                <span class="badge" style="background-color: {status_color}; color: {status_text_color}; border: 1px solid {status_text_color};">
                    {status}
                </span>
            </div>
            <div class="metrics-grid">
                <div class="metric">
                    <span class="label">Max Depth</span>
                    <span class="value">{data.get('max_depth_m', 0.0):.4f} m</span>
                </div>
                <div class="metric">
                    <span class="label">Flooded Area</span>
                    <span class="value">{data.get('flooded_area_pct', 0.0):.1f}%</span>
                </div>
                <div class="metric">
                    <span class="label">Mass Error</span>
                    <span class="value">{data.get('absolute_mass_error', 0.0):.3e} m³</span>
                </div>
            </div>
            <p class="msg">{data.get('message', '')}</p>
            <div class="chart-tabs">
                <div class="tab-buttons">
                    <button class="tab-btn active" onclick="switchTab(this, 'hydrograph-{name}')">Hydrograph</button>
                    <button class="tab-btn" onclick="switchTab(this, 'histogram-{name}')">Depth Hist</button>
                    <button class="tab-btn" onclick="switchTab(this, 'mass-{name}')">Mass Balance</button>
                    <button class="tab-btn" onclick="switchTab(this, 'flooded-{name}')">Flooded Area</button>
                    <button class="tab-btn" onclick="switchTab(this, 'drain-{name}')">Drain Util</button>
                    <button class="tab-btn" onclick="switchTab(this, 'outfall-{name}')">Outfall Util</button>
                </div>
                <div class="tab-content" id="hydrograph-{name}">
                    <img src="{hydro_url}" alt="Hydrograph plot" />
                </div>
                <div class="tab-content hidden" id="histogram-{name}">
                    <img src="{hist_url}" alt="Depth histogram plot" />
                </div>
                <div class="tab-content hidden" id="mass-{name}">
                    <img src="{mass_url}" alt="Mass balance plot" />
                </div>
                <div class="tab-content hidden" id="flooded-{name}">
                    <img src="{area_url}" alt="Flooded area vs time plot" />
                </div>
                <div class="tab-content hidden" id="drain-{name}">
                    <img src="{drain_url}" alt="Drain utilization plot" />
                </div>
                <div class="tab-content hidden" id="outfall-{name}">
                    <img src="{outfall_url}" alt="Outfall utilization plot" />
                </div>
            </div>
        </div>
        """

    # Kurla Case Study Section
    kurla_section = ""
    if kurla_summary:
        kurla_section = f"""
        <div class="card kurla-card">
            <div class="card-header">
                <h2>Validation Case Study: Kurla/BKC Area</h2>
                <span class="badge" style="background-color: rgba(59, 130, 246, 0.2); color: #3b82f6; border: 1px solid #3b82f6;">VALIDATED</span>
            </div>
            <div class="metrics-grid">
                <div class="metric">
                    <span class="label">Max Flood Depth</span>
                    <span class="value">{kurla_summary.get('max_depth_m', 0.0):.4f} m</span>
                </div>
                <div class="metric">
                    <span class="label">Mean Flood Depth</span>
                    <span class="value">{kurla_summary.get('mean_depth_m', 0.0):.4f} m</span>
                </div>
                <div class="metric">
                    <span class="label">Flooded Area</span>
                    <span class="value">{kurla_summary.get('flooded_pct', 0.0):.1f}%</span>
                </div>
                <div class="metric">
                    <span class="label">Peak Flow Velocity</span>
                    <span class="value">{kurla_summary.get('peak_velocity_m_s', 0.0):.3f} m/s</span>
                </div>
            </div>
            <div class="chart-tabs">
                <div class="tab-buttons">
                    <button class="tab-btn active" onclick="switchTab(this, 'hydrograph-kurla')">Hydrograph</button>
                    <button class="tab-btn" onclick="switchTab(this, 'histogram-kurla')">Depth Hist</button>
                    <button class="tab-btn" onclick="switchTab(this, 'mass-kurla')">Mass Balance</button>
                    <button class="tab-btn" onclick="switchTab(this, 'flooded-kurla')">Flooded Area</button>
                    <button class="tab-btn" onclick="switchTab(this, 'drain-kurla')">Drain Util</button>
                </div>
                <div class="tab-content" id="hydrograph-kurla">
                    <img src="plots/kurla/hydrograph.png" alt="Hydrograph plot" />
                </div>
                <div class="tab-content hidden" id="histogram-kurla">
                    <img src="plots/kurla/water_depth_histogram.png" alt="Depth histogram plot" />
                </div>
                <div class="tab-content hidden" id="mass-kurla">
                    <img src="plots/kurla/mass_balance.png" alt="Mass balance plot" />
                </div>
                <div class="tab-content hidden" id="flooded-kurla">
                    <img src="plots/kurla/flooded_area_vs_time.png" alt="Flooded area vs time plot" />
                </div>
                <div class="tab-content hidden" id="drain-kurla">
                    <img src="plots/kurla/drain_utilization.png" alt="Drain utilization plot" />
                </div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Urban Hydrodynamic Simulation Platform (UHSP) — Validation Dashboard</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --border-color: rgba(255, 255, 255, 0.1);
            --text-color: #f1f5f9;
            --accent-color: #38bdf8;
        }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 2rem;
            line-height: 1.5;
        }}
        header {{
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1rem;
        }}
        h1 {{
            color: var(--accent-color);
            margin: 0;
            font-size: 2.2rem;
            font-weight: 800;
        }}
        .sys-info {{
            font-size: 0.9rem;
            color: #94a3b8;
            margin-top: 0.5rem;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }}
        @media(min-width: 768px) {{
            .grid {{
                grid-template-columns: 1fr 1fr;
            }}
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }}
        .kurla-card {{
            grid-column: 1 / -1;
            border: 1px solid rgba(59, 130, 246, 0.4);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        .card-header h3, .card-header h2 {{
            margin: 0;
            font-weight: 700;
        }}
        .badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 1rem;
            background: rgba(0, 0, 0, 0.2);
            padding: 1rem;
            border-radius: 8px;
        }}
        .metric {{
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .metric .label {{
            font-size: 0.8rem;
            color: #94a3b8;
        }}
        .metric .value {{
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--accent-color);
        }}
        .msg {{
            font-size: 0.85rem;
            color: #cbd5e1;
            margin-bottom: 1rem;
        }}
        .tab-buttons {{
            display: flex;
            gap: 0.25rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
            overflow-x: auto;
        }}
        .tab-btn {{
            background: transparent;
            border: none;
            color: #94a3b8;
            padding: 0.5rem 0.75rem;
            font-size: 0.8rem;
            cursor: pointer;
            border-radius: 4px;
            white-space: nowrap;
        }}
        .tab-btn.active {{
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent-color);
            font-weight: 600;
        }}
        .tab-content img {{
            width: 100%;
            height: auto;
            border-radius: 6px;
            border: 1px solid var(--border-color);
        }}
        .hidden {{
            display: none;
        }}
    </style>
    <script>
        function switchTab(btn, contentId) {{
            // Deactivate all buttons in this tab row
            let tabGroup = btn.parentElement;
            let btns = tabGroup.getElementsByClassName('tab-btn');
            for(let b of btns) {{
                b.classList.remove('active');
            }}
            btn.classList.add('active');
            
            // Hide all content tabs in this card
            let card = tabGroup.parentElement;
            let contents = card.getElementsByClassName('tab-content');
            for(let c of contents) {{
                c.classList.add('hidden');
            }}
            document.getElementById(contentId).classList.remove('hidden');
        }}
    </script>
</head>
<body>
    <div class="container">
        <header>
            <h1>Urban Hydrodynamic Simulation Platform (UHSP) — Scientific Validation Dashboard</h1>
            <div class="sys-info">
                Executed: {sys_profile['timestamp']} | OS: {sys_profile['os']} | Python: {sys_profile['python_ver']}
            </div>
        </header>
        <div class="grid">
            {kurla_section}
            {benchmark_cards}
        </div>
    </div>
</body>
</html>
"""
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Interactive dashboard successfully compiled: {DASHBOARD_PATH}")


if __name__ == "__main__":
    compile_dashboard()
