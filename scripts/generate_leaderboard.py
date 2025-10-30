#!/usr/bin/env python3
import os
import json
import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
HTML_DIR = REPO_ROOT / "html"
OUTPUT_HTML = HTML_DIR / "index.html"


def read_json_file(file_path: Path):
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def discover_benchmarks():
    benchmarks = {}
    if not BENCHMARKS_DIR.exists():
        return benchmarks

    for item in BENCHMARKS_DIR.iterdir():
        if not item.is_dir():
            continue
        info = read_json_file(item / "info.json") or {}
        readme_path = item / "README.md"
        benchmarks[item.name] = {
            "name": info.get("name", item.name),
            "description": info.get("description", ""),
            "tags": info.get("tags", []),
            "readme": readme_path.relative_to(REPO_ROOT).as_posix()
            if readme_path.exists()
            else None,
        }
    return benchmarks


def parse_result_file(result_file: Path):
    data = read_json_file(result_file)
    if not isinstance(data, dict):
        return None
    commit = data.get("commit")
    date_str = data.get("date")
    result_value = data.get("result")

    # Normalize date
    dt_iso = None
    if isinstance(date_str, str):
        try:
            dt_iso = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            dt_iso = None

    return {
        "commit": commit,
        "date": date_str,
        "date_obj": dt_iso,
        "result": result_value,
        "file": result_file.relative_to(REPO_ROOT).as_posix(),
    }


def discover_results():
    records = []
    if not RESULTS_DIR.exists():
        return records

    # Expected structure:
    # results/<code>/<machine>/<test_problem>/*.json
    for code_dir in RESULTS_DIR.iterdir():
        if not code_dir.is_dir():
            continue
        for machine_dir in code_dir.iterdir():
            if not machine_dir.is_dir():
                continue
            for test_dir in machine_dir.iterdir():
                if not test_dir.is_dir():
                    continue
                test_name = test_dir.name
                for json_file in test_dir.glob("*.json"):
                    parsed = parse_result_file(json_file)
                    if parsed is None:
                        continue
                    records.append(
                        {
                            "code": code_dir.name,
                            "machine": machine_dir.name,
                            "test": test_name,
                            **parsed,
                        }
                    )
    return records


def html_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def generate_html(benchmarks: dict, results: list) -> str:
    # Group results by test
    results_by_test = {}
    for rec in results:
        results_by_test.setdefault(rec["test"], []).append(rec)

    # Sort records within each test by result (ascending), then by date (newest first)
    for test_name, recs in results_by_test.items():
        recs.sort(
            key=lambda r: (
                r["result"] if r.get("result") is not None else float("inf"),
                -(r["date_obj"].timestamp() if r.get("date_obj") else 0),
            )
        )

    # Compute global stats
    unique_codes = sorted({r["code"] for r in results}) if results else []
    unique_machines = sorted({r["machine"] for r in results}) if results else []
    num_tests = len(results_by_test)
    num_results = len(results)
    last_dt = max(
        (r.get("date_obj") for r in results if r.get("date_obj")), default=None
    )
    last_dt_str = last_dt.strftime("%Y-%m-%d %H:%M:%S UTC") if last_dt else "N/A"

    # Build HTML
    parts = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    parts.append('  <meta charset="utf-8">')
    parts.append(
        '  <meta name="viewport" content="width=device-width, initial-scale=1">'
    )
    parts.append("  <title>AstroBenchmarks Leaderboard</title>")
    parts.append(
        "  <style>:root{--bg:#ffffff;--fg:#111;--muted:#666;--card:#f6f6f7;--border:#e5e5e5;--link:#0b63c6;--chip:#e9eef5;}\n"
        " [data-theme=dark]{--bg:#0f1116;--fg:#e6e6e6;--muted:#9aa0a6;--card:#171a21;--border:#2a2f3a;--link:#66a7ff;--chip:#1f2633;}\n"
        " html,body{height:100%;} body{background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Noto Sans,Helvetica,Arial,sans-serif; margin:0;}\n"
        " .container{max-width:1200px;margin:0 auto;padding:24px;}\n"
        " .topbar{position:sticky;top:0;z-index:10;background:var(--bg);border-bottom:1px solid var(--border);}\n"
        " .topbar-inner{display:flex;align-items:center;gap:16px;justify-content:space-between;max-width:1200px;margin:0 auto;padding:12px 24px;}\n"
        " .brand{display:flex;align-items:baseline;gap:12px;} .brand h1{font-size:20px;margin:0;} .muted{color:var(--muted);}\n"
        " .controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;}\n"
        " .search{padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--fg);}\n"
        " .btn{padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card);color:var(--fg);cursor:pointer;} .btn:hover{filter:brightness(0.98);}\n"
        " a{color:var(--link);} a:hover{text-decoration:none;filter:brightness(1.1);}\n"
        " .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:16px 0 24px;}\n"
        " .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;} .card .label{font-size:12px;color:var(--muted);} .card .value{font-weight:600;font-size:20px;}\n"
        " .layout{display:grid;grid-template-columns:220px 1fr;gap:24px;} @media(max-width:1000px){.layout{grid-template-columns:1fr;}}\n"
        " .sidebar{position:sticky;top:64px;align-self:start;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px;}\n"
        " .sidebar h3{margin:6px 8px;font-size:14px;color:var(--muted);} .nav{list-style:none;margin:0;padding:0;} .nav a{display:block;padding:8px 10px;border-radius:8px;color:var(--fg);} .nav a:hover{background:rgba(0,0,0,0.04);} [data-theme=dark] .nav a:hover{background:rgba(255,255,255,0.06);}\n"
        " .test-header{display:flex;align-items:baseline;gap:12px;margin-top:28px;} .nowrap{white-space:nowrap;} .small{font-size:12px;color:var(--muted);}\n"
        " .chip{display:inline-block;padding:2px 8px;border:1px solid var(--border);border-radius:999px;margin-right:6px;font-size:12px;background:var(--chip);}\n"
        " table{border-collapse:collapse;width:100%;margin:12px 0 32px;} th,td{border:1px solid var(--border);padding:10px;text-align:left;} th{background:var(--card);position:sticky;top:48px;z-index:1;}\n"
        " .best{background:linear-gradient(90deg,rgba(255,215,0,0.18),transparent);}\n"
        " .footer{margin:32px 0;color:var(--muted);}\n"
        " </style>"
    )
    parts.append(
        "  <script>\n"
        "(function(){\n"
        "  const stored=localStorage.getItem('ab_theme');\n"
        "  if(stored){document.documentElement.setAttribute('data-theme',stored);}\n"
        "})();\n"
        "function toggleTheme(){\n"
        "  const cur=document.documentElement.getAttribute('data-theme');\n"
        "  const next=cur==='dark'?'light':'dark';\n"
        "  document.documentElement.setAttribute('data-theme',next);\n"
        "  localStorage.setItem('ab_theme',next);\n"
        "}\n"
        "function filterRows(q){\n"
        "  q=(q||'').toLowerCase();\n"
        "  document.querySelectorAll('tbody tr.result-row').forEach(function(tr){\n"
        "    const t=(tr.getAttribute('data-test')+' '+tr.getAttribute('data-code')+' '+tr.getAttribute('data-machine')+' '+tr.textContent).toLowerCase();\n"
        "    tr.style.display = t.indexOf(q)>=0 ? '' : 'none';\n"
        "  });\n"
        "}\n"
        "function sortTable(tableId,col,asc){\n"
        "  const table=document.getElementById(tableId);\n"
        "  const tbody=table.querySelector('tbody');\n"
        "  const getVal=(tr)=>tr.children[col].getAttribute('data-sort')||tr.children[col].innerText;\n"
        "  const rows=Array.from(tbody.querySelectorAll('tr')).filter(r=>r.style.display!=='none');\n"
        "  rows.sort((a,b)=>{\n"
        "    const va=getVal(a); const vb=getVal(b);\n"
        "    const na=parseFloat(va); const nb=parseFloat(vb);\n"
        "    const bothNum = !isNaN(na) && !isNaN(nb);\n"
        "    const cmp = bothNum ? (na-nb) : va.localeCompare(vb);\n"
        "    return asc?cmp:-cmp;\n"
        "  });\n"
        "  rows.forEach(r=>tbody.appendChild(r));\n"
        "}\n"
        "</script>"
    )
    parts.append("</head>")
    parts.append("<body>")
    parts.append('  <div class="topbar"><div class="topbar-inner">')
    parts.append(
        '    <div class="brand"><h1>AstroBenchmarks Leaderboard</h1>'
        + f'<span class="muted">Updated {html_escape(datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"))}</span></div>'
    )
    parts.append('    <div class="controls">')
    parts.append(
        '      <input id="global-search" class="search" placeholder="Search code, machine, test, commit..." oninput="filterRows(this.value)">'
    )
    parts.append(
        '      <button class="btn" onclick="toggleTheme()">Toggle theme</button>'
    )
    parts.append("    </div>")
    parts.append("  </div></div>")
    parts.append('  <div class="container">')

    # Stats cards
    parts.append('  <div class="stats">')
    parts.append(
        f'    <div class="card"><div class="label">Tests</div><div class="value">{num_tests}</div></div>'
    )
    parts.append(
        f'    <div class="card"><div class="label">Results</div><div class="value">{num_results}</div></div>'
    )
    parts.append(
        f'    <div class="card"><div class="label">Codes</div><div class="value">{len(unique_codes)}</div></div>'
    )
    parts.append(
        f'    <div class="card"><div class="label">Machines</div><div class="value">{len(unique_machines)}</div></div>'
    )
    parts.append(
        f'    <div class="card"><div class="label">Last result</div><div class="value">{html_escape(last_dt_str)}</div></div>'
    )
    parts.append("  </div>")

    # Sidebar navigation
    parts.append('  <div class="layout">')
    parts.append('    <aside class="sidebar">')
    parts.append("      <h3>Tests</h3>")
    parts.append('      <ul class="nav">')
    for tname in sorted(results_by_test.keys()):
        parts.append(
            f'        <li><a href="#{html_escape(tname)}">{html_escape(tname)}</a></li>'
        )
    parts.append("      </ul>")
    parts.append("    </aside>")
    parts.append("    <main>")

    if not results_by_test:
        parts.append("  <p>No results found in <code>results/</code>.</p>")
    else:
        for test_name, recs in sorted(results_by_test.items()):
            meta = benchmarks.get(test_name, {})
            title = meta.get("name", test_name)
            desc = meta.get("description", "")
            tags = meta.get("tags", []) or []
            readme_rel = meta.get("readme")

            parts.append('  <div class="test-header">')
            parts.append(
                f'    <h2 id="{html_escape(test_name)}">{html_escape(title)}</h2>'
            )
            if readme_rel:
                parts.append(
                    f'    <a class="small" href="../{html_escape(readme_rel)}" target="_blank">README</a>'
                )
            parts.append("  </div>")
            if desc:
                parts.append(f'  <div class="muted">{html_escape(desc)}</div>')
            if tags:
                parts.append(
                    "  <div>"
                    + " ".join(
                        f'<span class="chip">{html_escape(t)}</span>' for t in tags
                    )
                    + "</div>"
                )

            # Identify best result row index for highlighting
            best_idx = None
            if recs:
                best_idx = 0

            parts.append("  <table>")
            table_id = f"table-{html_escape(test_name)}"
            parts.append(
                "    <thead><tr>"
                f"<th onclick=\"sortTable('{table_id}',0,true)\">Rank</th>"
                f"<th onclick=\"sortTable('{table_id}',1,true)\">Code</th>"
                f"<th onclick=\"sortTable('{table_id}',2,true)\">Machine</th>"
                f"<th onclick=\"sortTable('{table_id}',3,true)\">Commit</th>"
                f'<th class="nowrap" onclick="sortTable(\'{table_id}\',4,true)">Date (UTC)</th>'
                f"<th onclick=\"sortTable('{table_id}',5,true)\">Result</th>"
                f"<th onclick=\"sortTable('{table_id}',6,true)\">Run file</th>"
                "</tr></thead>"
            )
            parts.append(f'    <tbody id="{table_id}">')
            for idx, r in enumerate(recs, start=1):
                commit_disp = (r.get("commit") or "").strip()
                if commit_disp:
                    short_commit = commit_disp[:7]
                else:
                    short_commit = ""
                date_disp = ""
                if r.get("date_obj"):
                    date_disp = r["date_obj"].strftime("%Y-%m-%d %H:%M:%S")
                elif r.get("date"):
                    date_disp = r["date"]
                result_disp = r.get("result")
                best_class = (
                    " best" if best_idx is not None and idx == best_idx + 1 else ""
                )
                parts.append(
                    f'      <tr class="result-row{best_class}" data-test="{html_escape(test_name)}" data-code="{html_escape(r["code"])}" data-machine="{html_escape(r["machine"])}">'
                    f'<td data-sort="{idx}">{idx}</td>'
                    f'<td data-sort="{html_escape(r["code"])}">{html_escape(r["code"])}</td>'
                    f'<td data-sort="{html_escape(r["machine"])}">{html_escape(r["machine"])}</td>'
                    f'<td class="nowrap" data-sort="{html_escape(short_commit)}">{html_escape(short_commit) if short_commit else ""}</td>'
                    f'<td class="nowrap" data-sort="{html_escape(date_disp)}">{html_escape(date_disp)}</td>'
                    f'<td data-sort="{html_escape(result_disp if result_disp is not None else "")}">{html_escape(result_disp if result_disp is not None else "")}</td>'
                    f'<td data-sort="{html_escape(Path(r["file"]).name)}"><a href="../{html_escape(r["file"])}" target="_blank">{html_escape(Path(r["file"]).name)}</a></td>'
                    "</tr>"
                )
            parts.append("    </tbody>")
            parts.append("  </table>")

    parts.append("    </main>")
    parts.append("  </div>")
    parts.append('  <div class="footer container">Built with ❤️ — AstroBenchmarks</div>')
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts)


def main():
    benchmarks = discover_benchmarks()
    results = discover_results()

    HTML_DIR.mkdir(parents=True, exist_ok=True)
    html = generate_html(benchmarks, results)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
