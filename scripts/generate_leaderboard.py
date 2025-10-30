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
            "readme": readme_path.relative_to(REPO_ROOT).as_posix() if readme_path.exists() else None,
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
                    records.append({
                        "code": code_dir.name,
                        "machine": machine_dir.name,
                        "test": test_name,
                        **parsed,
                    })
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

    # Build HTML
    parts = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html lang=\"en\">")
    parts.append("<head>")
    parts.append("  <meta charset=\"utf-8\">")
    parts.append("  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">")
    parts.append("  <title>AstroBenchmarks Leaderboard</title>")
    parts.append(
        "  <style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,\n"
        " Noto Sans,Helvetica,Arial,sans-serif;padding:24px;max-width:1200px;margin:0 auto;}\n"
        " h1{margin:0 0 16px;} .muted{color:#666;} .chip{display:inline-block;padding:2px 8px;border:1px solid #ddd;border-radius:999px;margin-right:6px;font-size:12px;}\n"
        " table{border-collapse:collapse;width:100%;margin:12px 0 32px;} th,td{border:1px solid #e5e5e5;padding:8px 10px;text-align:left;} th{background:#fafafa;}\n"
        " .test-header{display:flex;align-items:baseline;gap:12px;margin-top:28px;} .nowrap{white-space:nowrap;}\n"
        " .small{font-size:12px;color:#666;} a{text-decoration:none;color:#0645ad;} a:hover{text-decoration:underline;}\n"
        " </style>"
    )
    parts.append("</head>")
    parts.append("<body>")
    parts.append("  <h1>AstroBenchmarks Leaderboard</h1>")
    parts.append(
        f"  <div class=\"muted\">Generated {html_escape(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ'))}</div>"
    )

    if not results_by_test:
        parts.append("  <p>No results found in <code>results/</code>.</p>")
    else:
        for test_name, recs in sorted(results_by_test.items()):
            meta = benchmarks.get(test_name, {})
            title = meta.get("name", test_name)
            desc = meta.get("description", "")
            tags = meta.get("tags", []) or []
            readme_rel = meta.get("readme")

            parts.append("  <div class=\"test-header\">")
            parts.append(f"    <h2 id=\"{html_escape(test_name)}\">{html_escape(title)}</h2>")
            if readme_rel:
                parts.append(
                    f"    <a class=\"small\" href=\"../{html_escape(readme_rel)}\" target=\"_blank\">README</a>"
                )
            parts.append("  </div>")
            if desc:
                parts.append(f"  <div class=\"muted\">{html_escape(desc)}</div>")
            if tags:
                parts.append(
                    '  <div>' + ' '.join(f'<span class="chip">{html_escape(t)}</span>' for t in tags) + '</div>'
                )

            parts.append("  <table>")
            parts.append(
                "    <thead><tr>"
                "<th>Rank</th><th>Code</th><th>Machine</th><th>Commit</th>"
                '<th class="nowrap">Date (UTC)</th><th>Result</th><th>Run file</th>'
                "</tr></thead>"
            )
            parts.append("    <tbody>")
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
                parts.append(
                    "      <tr>"
                    f"<td>{idx}</td>"
                    f"<td>{html_escape(r['code'])}</td>"
                    f"<td>{html_escape(r['machine'])}</td>"
                    f'<td class="nowrap">{html_escape(short_commit) if short_commit else ''}</td>'
                    f'<td class="nowrap">{html_escape(date_disp)}</td>'
                    f"<td>{html_escape(result_disp if result_disp is not None else '')}</td>"
                    f"<td><a href=\"../{html_escape(r['file'])}\" target=\"_blank\">{html_escape(Path(r['file']).name)}</a></td>"
                    "</tr>"
                )
            parts.append("    </tbody>")
            parts.append("  </table>")

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


