#!/usr/bin/env python3
# Wolf Works Releases v1; canonical source: Wolf-Works-LLC/hq/scripts/releases/post.py
"""Render or deliver release messages. Only trusted default-branch code runs here."""
import argparse
import fnmatch
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import uuid

VERSION = "v1"
HERE = Path(__file__).resolve().parent


def api(path):
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("GitHub metadata unavailable")
    return json.loads(re.sub(r"\x1b\[[0-9;]*m", "", result.stdout))


def pages(path, key=None):
    """Fail closed on API/pagination errors instead of reporting a partial range."""
    for page in range(1, 101):
        data = api(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        rows = data[key] if key else data
        yield from rows
        if len(rows) < 100:
            return
    raise RuntimeError("GitHub pagination limit exceeded")


def safe(value, limit=500):
    # Escape Slack's explicit mention/link syntax, including <!channel> and <@U…>.
    value = str(value).replace("\r", " ").replace("\n", " ")
    return html.escape(value[:limit], quote=False).replace("@", "＠").replace("`", "'")


def person(login, names):
    return safe(names.get(login, f"{login} (name not mapped)"), 100)


def section(text):
    return {"type": "section", "text": {"type": "mrkdwn", "text": text, "verbatim": True}}


def link(url, label):
    # All destinations are constructed locally from verified GitHub fields.
    return f"<{url}|{label}>"


def render(record, names, channel):
    kind = record["kind"]
    repo = safe(record["repo"])
    labels = {"merge": ("#2f7ed8", "🔵 Merged to main"),
              "production": ("#2eb67d", "🚀 Live in production"),
              "rollback": ("#e01e5a", "↩︎ Rolled back")}
    color, title = labels[kind]
    if kind == "merge":
        title = "🔵 Merged to " + safe(record.get("branch", "main"), 100)
    label = f" · {safe(record['target'])}" if record.get("target") else ""
    heading = f"{title} · {repo}{label}"
    blocks = [section(f"*{heading}*")]
    if kind == "merge":
        pr = record["pr"]
        blocks.append(section(f"{link(pr['url'], '#' + str(pr['number']))} · {safe(pr['title'])}\n"
                              f"By {person(pr['author'], names)} · merged by {person(pr['merger'], names)}"))
    else:
        if kind == "rollback":
            blocks.append(section(f"Rolled back to `{safe(record['sha'], 40)}`\nReason: {safe(record['reason'], 1000)}"))
        groups = {}
        for pr in record.get("prs", []):
            # Checked-in PR labels provide stable areas; titles remain exact rather than invented prose.
            area = next((x[5:] for x in pr.get("labels", []) if x.startswith("area:")), "Engineering")
            groups.setdefault(area, []).append(pr)
        if groups:
            blocks.append(section("*What's new*"))
            count = 0
            for area, prs in groups.items():
                if count >= 35:
                    break
                lines = [f"*{safe(area, 80)}*"]
                for pr in prs[:8]:
                    lines.append(f"• {safe(pr['title'], 220)} ({link(pr['url'], '#' + str(pr['number']))}, {person(pr['author'], names)})")
                if len(prs) > 8:
                    lines.append(f"• {len(prs) - 8} more changes; see full comparison")
                blocks.append(section("\n".join(lines)[:2900]))
                count += 1
        else:
            blocks.append(section(record.get("notice", "No merged PRs in this deployment range.")))
        blocks.append(section(f"Deployed by {person(record['actor'], names)} · `{safe(record['sha'][:12])}`"))
    refs = [link(record["run_url"], "Run")]
    if record.get("compare_url"):
        refs.append(link(record["compare_url"], "Full changes"))
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": " · ".join(refs)}]})
    return {"channel": channel, "text": heading, "parse": "none", "link_names": False,
            "unfurl_links": False, "unfurl_media": False,
            "client_msg_id": str(uuid.uuid5(uuid.NAMESPACE_URL, record["key"])),
            "attachments": [{"color": color, "blocks": blocks}]}


def successful_job(repo, run_id, job_name, required_step=None):
    matches = [j for j in pages(f"repos/{repo}/actions/runs/{run_id}/jobs?filter=latest", "jobs")
               if j["name"] == job_name]
    return bool(matches) and all(j["conclusion"] == "success" and (
        not required_step or any(s["name"] == required_step and s["conclusion"] == "success"
                                 for s in j.get("steps", []))) for j in matches)


def production_record(repo, run, target):
    job = target["job"]
    if not successful_job(repo, run["id"], job, target.get("required_step")):
        return None  # A green workflow with a skipped deployment is NOT a deploy.
    base = None
    for previous in pages(f"repos/{repo}/actions/workflows/{run['workflow_id']}/runs?status=completed", "workflow_runs"):
        if (previous["id"] == run["id"] or previous["run_number"] >= run["run_number"]
                or previous.get("event") not in ("push", "workflow_dispatch")
                or not any(fnmatch.fnmatch(previous.get("head_branch", ""), branch)
                           for branch in target.get("branches", ["main"]))):
            continue
        if successful_job(repo, previous["id"], job, target.get("required_step")):
            base = previous["head_sha"]
            break
    sha = run["head_sha"]
    record = {"kind": "production", "repo": repo, "target": target["target"], "sha": sha,
              "actor": (run.get("triggering_actor") or run["actor"])["login"],
              "run_url": f"https://github.com/{repo}/actions/runs/{run['id']}",
              "key": f"{repo}:production:{run['id']}:{target['target']}", "prs": []}
    if not base:
        record["notice"] = "First observed production deployment; no previous successful deployment baseline."
        return record
    record["compare_url"] = f"https://github.com/{repo}/compare/{base}...{sha}"
    comparison = api(f"repos/{repo}/compare/{base}...{sha}?per_page=100")
    if comparison["status"] not in ("ahead", "identical"):
        record["kind"] = "rollback"
        record["reason"] = "Production revision moved backward or diverged from the previous successful deployment."
        return record
    seen = set()
    for commit in pages(f"repos/{repo}/compare/{base}...{sha}", "commits"):
        for pr in pages(f"repos/{repo}/commits/{commit['sha']}/pulls"):
            if pr.get("merged_at") and pr["base"]["ref"] == "main" and pr["number"] not in seen:
                seen.add(pr["number"])
                record["prs"].append({"number": pr["number"], "title": pr["title"],
                                      "url": f"https://github.com/{repo}/pull/{pr['number']}",
                                      "author": pr["user"]["login"],
                                      "labels": [x["name"] for x in pr.get("labels", [])]})
    return record


def records(event, repo, config):
    if repo not in config["repositories"]:
        raise ValueError("Repository not enrolled")
    pr = event.get("pull_request")
    if pr:
        branch = config["repositories"][repo].get("default_branch", "main")
        if (event.get("action") != "closed" or not pr.get("merged") or pr["base"]["ref"] != branch
                or pr["base"]["repo"]["full_name"] != repo):
            return []
        return [{"kind": "merge", "repo": repo, "branch": branch,
                 "pr": {"number": pr["number"], "title": pr["title"],
                        "url": f"https://github.com/{repo}/pull/{pr['number']}",
                        "author": pr["user"]["login"], "merger": pr["merged_by"]["login"]},
                 "run_url": f"https://github.com/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '0')}",
                 "key": f"{repo}:merge:{pr['number']}:{pr['merge_commit_sha']}"}]
    run = event.get("workflow_run")
    if not run or event.get("action") != "completed":
        return []
    if (run.get("event") not in ("push", "workflow_dispatch")
            or (run.get("head_repository") or {}).get("full_name") != repo):
        return []
    result = []
    for target in config["repositories"][repo].get("deployments", []):
        if run["path"] != target["workflow"]:
            continue
        if not any(fnmatch.fnmatch(run.get("head_branch", ""), branch)
                   for branch in target.get("branches", ["main"])):
            continue
        record = production_record(repo, run, target)
        if record:
            result.append(record)
    return result


def deliver(payload):
    token = os.environ.get("WOLFWORKS_RELEASES_SLACK_TOKEN")
    if not token or not payload["channel"]:
        print("::warning::Release notification not delivered: Slack token or channel is missing.")
        return False
    request = urllib.request.Request("https://slack.com/api/chat.postMessage",
                                     data=json.dumps(payload).encode(), method="POST",
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
        if not result.get("ok"):
            print("::warning::Slack rejected release notification; check app membership and configuration.")
            return False
        print("Release notification delivered.")
        return True
    except Exception:
        # Never print request objects, API error bodies, headers, or exception text.
        # Do not retry an uncertain delivery: Slack might have accepted it already.
        print("::warning::Slack delivery failed; release status is unchanged. Inspect Slack before retrying.")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--record", help="Offline normalized record fixture (no GitHub calls)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    names = json.loads((HERE / "names.json").read_text())
    channel = os.environ.get("RELEASES_SLACK_CHANNEL_ID", "")
    try:
        items = [json.loads(Path(args.record).read_text())] if args.record else records(
            json.loads(Path(args.event).read_text()), args.repo, json.loads((HERE / "repositories.json").read_text()))
        payloads = [render(item, names, channel) for item in items]
        if args.dry_run:
            print(json.dumps(payloads, ensure_ascii=False, indent=2))
        else:
            for payload in payloads:
                deliver(payload)
    except Exception:
        if args.dry_run:
            raise
        print("::warning::Release metadata/rendering failed; merge or deploy status is unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
