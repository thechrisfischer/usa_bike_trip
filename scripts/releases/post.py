#!/usr/bin/env python3
# Wolf Works Releases notifier v2; canonical source: Wolf-Works-LLC/hq/scripts/releases/post.py
"""Render or deliver release messages. Only trusted default-branch code runs here."""

import argparse
import fnmatch
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

VERSION = "v2"
HERE = Path(__file__).resolve().parent


def api(path):
    gh = shutil.which("gh")
    if not gh:
        raise RuntimeError("GitHub CLI unavailable")
    # Trusted executable, fixed subcommand, one endpoint argument; no shell.
    result = subprocess.run([gh, "api", path], capture_output=True, text=True)  # noqa: S603
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


REPORTING_MESSAGE = "Release reporting turned on; no change to the product."
ENROLLMENT_FILES = {
    ".github/workflows/labs-releases.yml",
    "scripts/releases/post.py",
    "scripts/releases/names.json",
    "scripts/releases/repositories.json",
}


def description_sections(body):
    """Keep descriptive prose, not test instructions, templates, links or code."""
    body = re.sub(r"<!--.*?-->", "", body or "", flags=re.S)
    sections = {}
    heading = ""
    fenced = False
    for raw in body.splitlines():
        if raw.strip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r"^\s*#{1,6}\s+(.+?)\s*#*\s*$", raw)
        if match:
            heading = re.sub(r"[^a-z ]", "", match[1].lower()).strip()
            continue
        if re.match(r"^\s*[-*]\s*\[[ xX]\]", raw):
            continue
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", raw)
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", text).strip()
        text = re.sub(r"[*_`]", "", text)
        if len(text) < 12 or re.match(
            r"^(?:n/?a|none|todo|describe |add (?:a |your )?description|no description)",
            text,
            re.I,
        ):
            continue
        if any(
            word in heading
            for word in ("test", "validat", "evidence", "rollback", "checklist", "implementation")
        ):
            continue
        sections.setdefault(heading, []).append(text)
    return sections


def description_field(sections, headings):
    for heading in headings:
        if sections.get(heading):
            return " ".join(sections[heading])[:650]
    return ""


def prose_excerpt(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


def change_description(pr):
    files = pr.get("files", [])
    complete = pr.get("files_complete", False) and bool(files)
    enrollment = (
        complete
        and all(path in ENROLLMENT_FILES for path in files)
        and bool(
            re.search(
                r"report (?:main )?merges|(?:enable|connect|turn on).*release reporting",
                pr["title"],
                re.I,
            )
        )
    )
    reporting = complete and all(
        path.startswith(("scripts/releases/", ".github/workflows/releases-"))
        or path in ENROLLMENT_FILES
        or path == "RELEASES_SMOKE_TEST.md"
        or path.startswith("docs/plans/release-message-")
        for path in files
    )
    internal = complete and all(
        path.startswith((".github/", "tests/", "docs/"))
        or path in {"README.md", "AGENTS.md", "CLAUDE.md"}
        for path in files
    )
    sections = description_sections(pr.get("body"))
    outcome = description_field(
        sections,
        (
            "reviewed release description",
            "release description",
            "release outcome",
            "outcome",
            "result",
            "resulting behavior",
            "what changed",
            "changes",
            "change",
            "summary",
        ),
    )
    if not outcome:
        outcome = description_field(sections, ("",))
    problem = description_field(sections, ("previous problem", "problem", "before", "trigger"))
    audience = description_field(
        sections, ("who benefits", "who is affected", "affected people", "audience", "users")
    )
    benefit = description_field(sections, ("why", "why it matters", "benefit", "benefits"))
    if enrollment:
        return {
            "outcome": REPORTING_MESSAGE,
            "audience": "The team following releases.",
            "benefit": "",
            "product_change": False,
            "enrollment": True,
        }
    if (
        internal
        and not reporting
        and all(path.startswith((".github/", "tests/")) for path in files)
    ):
        return {
            "outcome": "Build checks or release automation changed; no change to the product.",
            "audience": "The team maintaining builds and releases.",
            "benefit": "",
            "product_change": False,
            "enrollment": False,
        }
    if not outcome:
        title = re.sub(
            r"^(?:feat|fix|chore|docs|test|ci|refactor)(?:\([^)]*\))?:\s*",
            "",
            pr["title"],
            flags=re.I,
        )
        scope = ", ".join(dict.fromkeys(path.split("/")[0] for path in files))
        outcome = f"Update described as: {title}."
        if scope:
            outcome += f" Changed scope: {scope}."
        outcome += " The effect on people was not described."
    elif problem and problem not in outcome:
        outcome = prose_excerpt(problem, 150).rstrip(".") + ". " + prose_excerpt(outcome, 350)
    if not audience and (reporting or internal):
        audience = "The team maintaining documentation, builds and release reporting."
    return {
        "outcome": outcome,
        "audience": audience,
        "benefit": benefit,
        "example": description_field(sections, ("example", "useful example")),
        "product_change": not (reporting or internal),
        "enrollment": False,
    }


def describe_pr(repo, pr):
    """Optional detail failures degrade to honest wording, never invented impact."""
    details = {"body": pr.get("body") or "", "files": [], "files_complete": False}
    try:
        full = pr if "changed_files" in pr else api(f"repos/{repo}/pulls/{pr['number']}")
        details["body"] = full.get("body") or details["body"]
        files = list(pages(f"repos/{repo}/pulls/{pr['number']}/files"))
        details["files"] = [file["filename"] for file in files]
        details["files_complete"] = len(files) == full["changed_files"]
    except Exception:
        print(
            "::warning::Optional PR description/file detail unavailable; impact stays unconfirmed."
        )
    return details


def render(record, names, channel):
    kind = record["kind"]
    color = {"merge": "#2f7ed8", "production": "#2eb67d", "rollback": "#e01e5a"}[kind]
    prs = [record["pr"]] if kind == "merge" else record.get("prs", [])
    descriptions = [change_description(pr) for pr in prs]
    lead_index = 0
    if kind == "production":
        lead_index = next((i for i, d in enumerate(descriptions) if d["product_change"]), 0)
    enrollment_only = bool(descriptions) and all(d["enrollment"] for d in descriptions)
    product_unchanged = bool(descriptions) and all(not d["product_change"] for d in descriptions)
    if kind == "merge":
        state = "Merged to " + safe(record.get("branch", "main"), 100)
        state += "; this post does not confirm a production deployment."
    elif kind == "rollback":
        state = "Rolled back in production."
    else:
        state = "Production deployment completed." if product_unchanged else "Live in production."
    if product_unchanged and not enrollment_only:
        state += " No product behavior changed."
    if kind == "rollback":
        outcome = "Production was restored to an earlier version. " + record["reason"]
    elif enrollment_only:
        outcome = REPORTING_MESSAGE
    elif descriptions:
        outcome = descriptions[lead_index]["outcome"]
    else:
        outcome = "A production deployment completed, but its effect on people is not described."
    blocks = [section(safe(outcome, 550)), section(f"*Status:* {state}")]
    if not descriptions and record.get("notice"):
        blocks.append(section(safe(record["notice"], 400)))
    audiences = list(dict.fromkeys(d["audience"] for d in descriptions if d["audience"]))
    if audiences:
        blocks.append(section("*Who is affected:* " + safe(" ".join(audiences), 350)))
    elif descriptions:
        blocks.append(section("Who is affected is not specified in the release description."))
    if descriptions and descriptions[lead_index]["benefit"]:
        blocks.append(
            section("*Why it matters:* " + safe(descriptions[lead_index]["benefit"], 400))
        )
    if descriptions and descriptions[lead_index].get("example"):
        blocks.append(section("*Example:* " + safe(descriptions[lead_index]["example"], 400)))
    if kind != "merge" and not enrollment_only:
        groups = {}
        for index, pr in enumerate(prs):
            if index == lead_index:
                continue
            description = descriptions[index]
            area = next(
                (x[5:] for x in pr.get("labels", []) if x.startswith("area:")), "Engineering"
            )
            groups.setdefault(area, []).append(description["outcome"])
        for count, (area, outcomes) in enumerate(groups.items()):
            if count >= 12:
                break
            for text in outcomes[:3]:
                blocks.append(section(f"*{safe(area, 60)}*\n{safe(text, 450)}"))
    refs = [safe(record["repo"], 150)]
    if record.get("target"):
        refs.append(safe(record["target"], 100))
    if kind == "merge":
        refs.extend(
            [
                f"By {person(prs[0]['author'], names)}",
                f"merged by {person(prs[0]['merger'], names)}",
            ]
        )
    else:
        refs.append(f"Deployed by {person(record['actor'], names)}")
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": " · ".join(refs)}]})
    evidence = [link(pr["url"], "#" + str(pr["number"])) for pr in prs[:8]]
    evidence.append(link(record["run_url"], "Run"))
    if record.get("compare_url"):
        evidence.append(link(record["compare_url"], "Full changes"))
    blocks.append(
        {"type": "context", "elements": [{"type": "mrkdwn", "text": " · ".join(evidence)}]}
    )
    return {
        "channel": channel,
        "text": safe(outcome, 550) + " " + state,
        "parse": "none",
        "link_names": False,
        "unfurl_links": False,
        "unfurl_media": False,
        "client_msg_id": str(uuid.uuid5(uuid.NAMESPACE_URL, record["key"])),
        "attachments": [{"color": color, "blocks": blocks}],
    }


def successful_job(repo, run_id, job_name, required_step=None):
    matches = [
        j
        for j in pages(f"repos/{repo}/actions/runs/{run_id}/jobs?filter=latest", "jobs")
        if j["name"] == job_name
    ]
    return bool(matches) and all(
        j["conclusion"] == "success"
        and (
            not required_step
            or any(
                s["name"] == required_step and s["conclusion"] == "success"
                for s in j.get("steps", [])
            )
        )
        for j in matches
    )


def production_record(repo, run, target):
    job = target["job"]
    if not successful_job(repo, run["id"], job, target.get("required_step")):
        return None  # A green workflow with a skipped deployment is NOT a deploy.
    base = None
    for previous in pages(
        f"repos/{repo}/actions/workflows/{run['workflow_id']}/runs?status=completed",
        "workflow_runs",
    ):
        if (
            previous["id"] == run["id"]
            or previous["run_number"] >= run["run_number"]
            or previous.get("event") not in ("push", "workflow_dispatch")
            or not any(
                fnmatch.fnmatch(previous.get("head_branch", ""), branch)
                for branch in target.get("branches", ["main"])
            )
        ):
            continue
        if successful_job(repo, previous["id"], job, target.get("required_step")):
            base = previous["head_sha"]
            break
    sha = run["head_sha"]
    record = {
        "kind": "production",
        "repo": repo,
        "target": target["target"],
        "sha": sha,
        "actor": (run.get("triggering_actor") or run["actor"])["login"],
        "run_url": f"https://github.com/{repo}/actions/runs/{run['id']}",
        "key": f"{repo}:production:{run['id']}:{target['target']}",
        "prs": [],
    }
    if not base:
        record["notice"] = (
            "First observed production deployment; no previous successful deployment baseline."
        )
        return record
    record["compare_url"] = f"https://github.com/{repo}/compare/{base}...{sha}"
    comparison = api(f"repos/{repo}/compare/{base}...{sha}?per_page=100")
    if comparison["status"] not in ("ahead", "identical"):
        record["kind"] = "rollback"
        record["reason"] = (
            "Production revision moved backward or diverged "
            "from the previous successful deployment."
        )
        return record
    seen = set()
    for commit in pages(f"repos/{repo}/compare/{base}...{sha}", "commits"):
        for pr in pages(f"repos/{repo}/commits/{commit['sha']}/pulls"):
            if pr.get("merged_at") and pr["base"]["ref"] == "main" and pr["number"] not in seen:
                seen.add(pr["number"])
                record["prs"].append(
                    {
                        "number": pr["number"],
                        "title": pr["title"],
                        "url": f"https://github.com/{repo}/pull/{pr['number']}",
                        "author": pr["user"]["login"],
                        "labels": [x["name"] for x in pr.get("labels", [])],
                        **describe_pr(repo, pr),
                    }
                )
    return record


def records(event, repo, config):
    if repo not in config["repositories"]:
        raise ValueError("Repository not enrolled")
    pr = event.get("pull_request")
    if pr:
        branch = config["repositories"][repo].get("default_branch", "main")
        if (
            event.get("action") != "closed"
            or not pr.get("merged")
            or pr["base"]["ref"] != branch
            or pr["base"]["repo"]["full_name"] != repo
        ):
            return []
        run_id = os.environ.get("GITHUB_RUN_ID", "0")
        return [
            {
                "kind": "merge",
                "repo": repo,
                "branch": branch,
                "pr": {
                    "number": pr["number"],
                    "title": pr["title"],
                    "url": f"https://github.com/{repo}/pull/{pr['number']}",
                    "author": pr["user"]["login"],
                    "merger": pr["merged_by"]["login"],
                    **describe_pr(repo, pr),
                },
                "run_url": f"https://github.com/{repo}/actions/runs/{run_id}",
                "key": f"{repo}:merge:{pr['number']}:{pr['merge_commit_sha']}",
            }
        ]
    run = event.get("workflow_run")
    if not run or event.get("action") != "completed":
        return []
    if (
        run.get("event") not in ("push", "workflow_dispatch")
        or (run.get("head_repository") or {}).get("full_name") != repo
    ):
        return []
    result = []
    for target in config["repositories"][repo].get("deployments", []):
        if run["path"] != target["workflow"]:
            continue
        if not any(
            fnmatch.fnmatch(run.get("head_branch", ""), branch)
            for branch in target.get("branches", ["main"])
        ):
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
    request = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        # Request URL is the fixed HTTPS Slack endpoint above, never caller input.
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            result = json.load(response)
        if not result.get("ok"):
            print(
                "::warning::Slack rejected release notification; "
                "check app membership and configuration."
            )
            return False
        print("Release notification delivered.")
        return True
    except Exception:
        # Never print request objects, API error bodies, headers, or exception text.
        # Do not retry an uncertain delivery: Slack might have accepted it already.
        print(
            "::warning::Slack delivery failed; release status is unchanged. "
            "Inspect Slack before retrying."
        )
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
        items = (
            [json.loads(Path(args.record).read_text())]
            if args.record
            else records(
                json.loads(Path(args.event).read_text()),
                args.repo,
                json.loads((HERE / "repositories.json").read_text()),
            )
        )
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
