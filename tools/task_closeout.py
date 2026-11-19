"""Check a project-local delivery, closure, retrospective and proposed publication.

The host supplies the real user/assistant message evidence for the current
delivery. This tool neither declares engineering acceptance nor sends messages
or submissions. It reads evidence and produces an immutable local receipt.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from backends.process.feedback import canonical_sha
from tools.product_contract import skill_location

STATE_SCHEMA = "chemical-task-closeout-v1"
TARGET_REPO = "milklong888/chemical-engineering-experience-inbox"


def schema():
    return {
        "schema": STATE_SCHEMA, "identity": ["task_id", "task_revision (positive integer)"],
        "references": "{path,sha256} under the declared evidence root",
        "common": ["operation", "task_id", "task_revision (except status)",
                   "previous_ref (optional exact current receipt, otherwise uses the local task head)"],
        "operations": {
            "status": ["Read the current closeout state for task_id without advancing the task"],
            "delivery": ["subject", "artifact_refs[]", "draft_ref (UTF-8 delivered reply draft)",
                         "feedback_question (optional custom wording)"],
            "delivery_sent": ["message_ref (assistant source with message_text/source_message_id/source_locator)"],
            "reply": ["message_ref (user source with actor/user_quote/source_message_id/source_locator)",
                      "has_change_request (actual current-scope change requested)",
                      "Explicit closure must follow the sent delivery in the same host conversation",
                      "An explicit publication withdrawal must follow its approval in the same host conversation"],
            "retrospective": ["review_ref (UTF-8 local issue/experience review)", "professional_materials[]",
                              "no_material_reason (if empty)", "named_items_ref ({items:[{id,summary,source_locator}]})",
                              "named_item_outcomes[] ({id,disposition,reason,evidence_refs})",
                              "batch_id", "batch_version", "proposals[] (or no_proposals_reason)"],
            "batch_presented": ["message_ref (actual assistant message with the exact table inline or its Markdown link)",
                                "table_ref (exact UTF-8 Markdown from upload_table_markdown)", "batch_sha256"],
            "approve_upload": ["message_ref (actual user reply ordered after the batch presentation)", "batch_sha256", "approved_rows[]"],
        },
        "publication_message_order": ["source_conversation_id (same actual conversation for each approval chain)",
                                      "source_message_index (positive integer, original host message order)"],
        "closure_message_order": ["Use the actual source_conversation_id and source_message_index on the sent delivery and explicit closure reply"],
        "professional_material": ["title", "scope", "body_ref (UTF-8 Markdown or text)",
                                  "source_refs[]", "verification"],
        "proposal_row": ["id (display row)", "entry_id (repository identity)", "title", "category", "public_ref (UTF-8 Markdown)",
                         "disclosure_basis", "scope", "verification", "new_value",
                         "target_repo", "attribution", "license"],
        "publication": "Local evidence and exact-row authorization only. Use the inbox protocol to check duplicate/PR and admission states.",
    }


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def reference(root, ref):
    require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}
            and text(ref["path"]) and isinstance(ref["sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", ref["sha256"], re.I), "Use an exact path and SHA-256 reference")
    path = (root / ref["path"]).resolve()
    require(path.is_relative_to(root), "Source points outside the declared evidence root")
    with path.open("rb") as handle:
        require(hashlib.file_digest(handle, "sha256").hexdigest() == ref["sha256"].lower(), "Referenced bytes changed")
    return path


def json_ref(root, ref):
    value = json.loads(reference(root, ref).read_text(encoding="utf-8-sig"))
    require(isinstance(value, dict), "Referenced JSON must be an object")
    return value


def text_ref(root, ref, *, suffixes=(".md", ".txt")):
    path = reference(root, ref)
    require(path.suffix.lower() in suffixes, "Supply reviewable UTF-8 prose")
    value = path.read_text(encoding="utf-8-sig")
    require(text(value) and "\x00" not in value, "Referenced text is empty or invalid")
    return value


def evidence(root, refs):
    require(isinstance(refs, list) and refs, "List the supporting source files")
    return [reference(root, ref) for ref in refs]


def closure_checker():
    location = skill_location()
    require(location["available"], "The installed skill reference is unavailable")
    owner = Path(location["path"]).parents[1] / "chemical-engineering-expert/scripts/evaluate_learning_eligibility.py"
    spec = importlib.util.spec_from_file_location("closeout_learning_owner", owner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.explicit_close_quote


def user_message(root, ref):
    message = json_ref(root, ref)
    require(message.get("actor") == "user" and all(text(message.get(key))
            for key in ("user_quote", "source_message_id", "source_locator")), "Bind the original user reply")
    return message


def delivery(request, state, root):
    subject = request.get("subject")
    require(text(subject) and "\n" not in subject, "Identify this delivery in the question")
    evidence(root, request.get("artifact_refs"))
    draft = text_ref(root, request.get("draft_ref"))
    current_revision = request["task_revision"]
    if state:
        if current_revision == state["task_revision"]:
            require(state["subject"] == subject and state["artifact_refs"] == request["artifact_refs"],
                    "Changed delivery scope or artifacts need a new revision")
            if state["status"] != "DELIVERY_DRAFT_READY":
                require(state["draft_ref"] == request["draft_ref"], "This revision already has its delivered reply")
                return state
        else:
            require(current_revision > state["task_revision"], "Use a newer revision for a new delivery")
    suggested = f"{subject}这一版是否完成，还是有需要修改的地方？"
    question = request.get("feedback_question", suggested)
    if (not text(question) or question not in draft or subject not in draft
            or not re.search(r"是否|要不要|需要.*吗|\b(?:is|are|would|do)\b", question, re.I)
            or not re.search(r"完成|结束|结项|\b(?:complete|completed|finished|done)\b", question, re.I)):
        return {"schema": STATE_SCHEMA, "status": "DELIVERY_QUESTION_MISSING", "question": suggested,
                "task_id": request["task_id"], "task_revision": current_revision}
    return {"schema": STATE_SCHEMA, "status": "DELIVERY_DRAFT_READY", "task_id": request["task_id"],
            "task_revision": current_revision, "subject": subject, "question": question,
            "draft_ref": request["draft_ref"], "artifact_refs": request["artifact_refs"],
            "handled_user_messages": state.get("handled_user_messages", {}) if state else {},
            "publication_approval_messages": state.get("publication_approval_messages", {}) if state else {},
            "batch": None}


def sent_delivery_message(root, state, sent_ref):
    message = json_ref(root, sent_ref)
    require(message.get("actor") == "assistant" and all(text(message.get(field))
            for field in ("source_message_id", "source_locator", "message_text")), "Bind the actual assistant delivery message")
    draft = text_ref(root, state["draft_ref"])
    require(draft.strip() == message["message_text"].strip(), "The sent reply differs from the checked delivery draft")
    return message


def delivery_sent(request, state, root):
    require(state["status"] in {"DELIVERY_DRAFT_READY", "DELIVERED_AWAITING_FEEDBACK"},
            "Check the actual delivery draft before binding its sent message")
    sent_ref = request.get("message_ref")
    sent_delivery_message(root, state, sent_ref)
    require(state.get("delivery_message_ref", sent_ref) == sent_ref, "Already bound to a different delivery message")
    evidence(root, state["artifact_refs"])
    state["delivery_message_ref"] = sent_ref
    state["status"] = "DELIVERED_AWAITING_FEEDBACK"
    return state


def require_current_closure_order(root, state, message):
    sent = sent_delivery_message(root, state, state["delivery_message_ref"])
    later_message(message, sent, "Explicit closure must follow this revision's actual delivery in the same conversation")


def reply(request, state, root):
    require(state["status"] in {"DELIVERED_AWAITING_FEEDBACK", "WORKING", "RETROSPECTIVE_REQUIRED", "RETROSPECTIVE_RECORDED"},
            "Record a checked delivery draft first")
    message = user_message(root, request.get("message_ref"))
    message_id = message["source_message_id"]
    prior = state["handled_user_messages"].get(message_id)
    if prior is not None:
        require(prior == request["message_ref"]["sha256"], "Previously handled message ID refers to different bytes")
        return state
    change = request.get("has_change_request")
    require(type(change) is bool, "Interpret any current-scope change request in the actual user reply")
    state["handled_user_messages"][message_id] = request["message_ref"]["sha256"]
    if change:
        state["status"] = "WORKING"
        state.pop("closure_event", None)
        state.pop("closure_message_ref", None)
        state.pop("retrospective", None)
        state.pop("upload_table_markdown", None)
        state["batch"] = None
    elif state["status"] == "DELIVERED_AWAITING_FEEDBACK" and closure_checker()(message["user_quote"]):
        evidence(root, state["artifact_refs"])
        require_current_closure_order(root, state, message)
        state["status"] = "RETROSPECTIVE_REQUIRED"
        state["closure_event"] = {"schema": "user-task-closure-event-v1", "actor": "user", "event_type": "close_task",
                                  "task_id": state["task_id"], "task_revision": state["task_revision"],
                                  "user_quote": message["user_quote"], "source_message_id": message_id,
                                  "source_locator": message["source_locator"], "contains_change_request": False}
        state["closure_message_ref"] = request["message_ref"]
    elif state["status"] == "RETROSPECTIVE_RECORDED":
        withdraw_upload_grants(state, root, request["message_ref"], message)
    return state


def required_text_fields(row, fields):
    require(isinstance(row, dict) and all(text(row.get(key)) for key in fields),
            "Complete these fields: " + ", ".join(fields))


def proposed_table(batch, root):
    def cell(value):
        return value.replace("|", "\\|").replace("\n", " ")

    lines = [f'# 拟上传表 {batch["id"]} 第 {batch["version"]} 版', "",
             "| 行 | 拟公开原文 | 类型 | 公开依据 | 适用范围 | 验证 | 新增点 | 目标 | 署名 | 许可 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in batch["rows"].values():
        path = (root / row["public_ref"]["path"]).resolve().as_posix()
        link = f'[{row["title"]}](<{path}>)'
        fields = [row["id"], link, *(row[key] for key in ("category", "disclosure_basis", "scope", "verification",
                  "new_value"))] + [row["target_repo"] + "/proposals/" + row["entry_id"] + ".md",
                                   row["attribution"], row["license"]]
        lines.append("| " + " | ".join(cell(value) for value in fields) + " |")
    if not batch["rows"]:
        lines.append("| " + " | ".join(["—", cell(batch["no_proposals_reason"])] + ["—"] * 8) + " |")
    return "\n".join(lines) + "\n"


def retrospective(request, state, root):
    require(state["status"] in {"RETROSPECTIVE_REQUIRED", "RETROSPECTIVE_RECORDED"},
            "Explicit user closure for this revision is required")
    user_message(root, state["closure_message_ref"])
    evidence(root, state["artifact_refs"])
    text_ref(root, request.get("review_ref"))
    materials = request.get("professional_materials")
    require(isinstance(materials, list) and (materials or text(request.get("no_material_reason"))),
            "Provide professional material or explain why no reusable material emerged")
    for material in materials:
        required_text_fields(material, ("title", "scope", "verification"))
        text_ref(root, material.get("body_ref"))
        evidence(root, material.get("source_refs"))

    items = json_ref(root, request.get("named_items_ref")).get("items")
    outcomes = request.get("named_item_outcomes")
    require(isinstance(items, list) and isinstance(outcomes, list), "Supply the point-by-point record of user-named issues")
    for item in items:
        required_text_fields(item, ("id", "summary", "source_locator"))
    for item in outcomes:
        required_text_fields(item, ("id", "disposition", "reason"))
        evidence(root, item.get("evidence_refs"))
    expected = {item["id"] for item in items}
    actual = {item["id"] for item in outcomes}
    require(actual == expected and len(actual) == len(items) == len(outcomes),
            "Account for every named item exactly once. Missing: " + ", ".join(sorted(expected - actual)))

    batch_id, version, proposals = request.get("batch_id"), request.get("batch_version"), request.get("proposals")
    require(text(batch_id) and type(version) is int and version > 0, "Name the current proposed upload batch and version")
    require(isinstance(proposals, list) and (proposals or text(request.get("no_proposals_reason"))),
            "List the proposed public drafts or explain the empty batch")
    rows = {}
    entry_ids = set()
    for row in proposals:
        required_text_fields(row, ("id", "entry_id", "title", "category", "scope", "disclosure_basis", "verification",
                                   "new_value", "target_repo", "attribution", "license"))
        id_, entry_id = row["id"], row["entry_id"]
        require(re.fullmatch(r"[A-Za-z0-9_-]+", id_) and id_ not in rows
                and re.fullmatch(r"EXP-[A-Za-z0-9_-]+", entry_id) and entry_id not in entry_ids
                and row["target_repo"] == TARGET_REPO,
                "Use a distinct row ID and the registered experience inbox")
        text_ref(root, row.get("public_ref"), suffixes=(".md",))
        require(not (set(row) - {"id", "entry_id", "title", "category", "scope", "disclosure_basis", "verification",
                                 "new_value", "target_repo", "attribution", "license", "public_ref"}),
                "Only the reviewed public draft is included in the proposed row")
        rows[id_] = row
        entry_ids.add(entry_id)
    previous = state["batch"]
    table = {"id": batch_id, "version": version, "rows": rows, "no_proposals_reason": request.get("no_proposals_reason")}
    digest = canonical_sha(table)
    if previous is not None and previous["id"] == batch_id:
        require(version > previous["version"] or digest == previous["sha256"], "Show a new table version after changing a row")
    stable = previous is not None and previous["id"] == batch_id
    authorized = {key: grant for key, grant in previous["authorizations"].items()
                  if key in rows and canonical_sha(rows[key]) == grant["row_sha256"]} if stable else {}
    state["batch"] = {**table, "sha256": digest, "authorizations": authorized}
    if stable and digest == previous["sha256"]:
        if "presentation" in previous:
            state["batch"]["presentation"] = previous["presentation"]
    else:
        state["upload_table_markdown"] = proposed_table(table, root)
    state["retrospective"] = {key: request.get(key) for key in
                              ("review_ref", "professional_materials", "no_material_reason",
                               "named_items_ref", "named_item_outcomes")}
    state["status"] = "RETROSPECTIVE_RECORDED"
    return state


def current_publication_batch(request, state):
    batch = state["batch"]
    require(state["status"] == "RETROSPECTIVE_RECORDED" and batch is not None
            and request.get("batch_sha256") == batch["sha256"], "Approval must identify the exact displayed upload batch")
    return batch


def message_position(message):
    conversation = message.get("source_conversation_id")
    index = message.get("source_message_index")
    require(text(conversation) and type(index) is int and index > 0,
            "Use the actual host conversation ID and positive message index")
    return conversation, index


def later_message(message, earlier, detail):
    conversation, index = message_position(message)
    earlier_conversation, earlier_index = message_position(earlier)
    require(conversation == earlier_conversation and index > earlier_index, detail)


def read_presentation(root, presentation):
    table_ref = presentation["table_ref"]
    table = text_ref(root, table_ref, suffixes=(".md",))
    message = json_ref(root, presentation["message_ref"])
    require(message.get("actor") == "assistant" and all(text(message.get(field))
            for field in ("source_message_id", "source_locator", "message_text")),
            "Bind the actual assistant message presenting the upload table")
    message_position(message)
    table_path = (root / table_ref["path"]).resolve().as_posix()
    body = message["message_text"].replace("\r\n", "\n")
    require(table.rstrip() in body or f"](<{table_path}>)" in body or f"]({table_path})" in body,
            "The actual assistant message must display or link the exact upload table")
    return table, message


def displayed_materials(root, state, batch, presentation):
    table, message = read_presentation(root, presentation)
    require(table == state["upload_table_markdown"], "The displayed Markdown must match the current proposed table exactly")
    for row in batch["rows"].values():
        text_ref(root, row["public_ref"], suffixes=(".md",))
    return message


def batch_presented(request, state, root):
    batch = current_publication_batch(request, state)
    presentation = {"table_ref": request.get("table_ref"), "message_ref": request.get("message_ref")}
    message = displayed_materials(root, state, batch, presentation)
    closure = user_message(root, state["closure_message_ref"])
    later_message(message, closure, "The upload table must be presented after this revision closed")
    require(batch.get("presentation", presentation) == presentation,
            "The current upload batch is already bound to a different presentation message")
    batch["presentation"] = presentation
    return state


def approve_upload(request, state, root):
    batch = current_publication_batch(request, state)
    presentation = batch.get("presentation")
    require(presentation is not None, "Record the actual presentation of this upload batch before accepting approval")
    quote_ref = request.get("message_ref")
    message = user_message(root, quote_ref)
    source_id = message["source_message_id"]
    require(quote_ref != state["closure_message_ref"]
            and source_id not in state["handled_user_messages"],
            "Closing the delivery does not approve publication")
    approval_source = {"message_sha256": quote_ref["sha256"], "batch_sha256": batch["sha256"]}
    approvals = state["publication_approval_messages"]
    require(approvals.get(source_id, approval_source) == approval_source,
            "An earlier approval cannot authorize a changed table")
    displayed = displayed_materials(root, state, batch, presentation)
    later_message(message, displayed, "The user approval must follow the displayed table in the same conversation")
    selection = request.get("approved_rows")
    require(isinstance(selection, list) and selection and len(selection) == len(set(selection))
            and set(selection) <= batch["rows"].keys(), "Name the rows explicitly approved for submission")
    quote = message["user_quote"]
    require(set(selection) <= explicitly_approved_rows(quote, batch["rows"]),
            "The user reply must authorize publication of these exact rows")
    for id_ in selection:
        row = batch["rows"][id_]
        text_ref(root, row["public_ref"], suffixes=(".md",))
        require_after_withdrawal(state, root, id_, message)
        existing = batch["authorizations"].get(id_)
        if existing and existing["message_ref"] != quote_ref:
            later_message(message, user_message(root, existing["message_ref"]),
                          "A replacement approval must follow the previous user approval")
        batch["authorizations"][id_] = {"row_sha256": canonical_sha(row), "batch_sha256": batch["sha256"],
                                         "message_ref": quote_ref, "source_message_id": source_id,
                                         "presentation": presentation}
    approvals[source_id] = approval_source
    return state


def hypothetical_publication_reply(quote):
    return re.search(
        r'[?？“”‘’「」『』"\x60]|(?:^|\n)\s*>|例如|比如|举例|举个例子|示例|样例|转述|引用|假设|假定|如果|假如|'
        r'除非|前提|是否|能否|能不能|\b(?:if|unless|example|suppose|quote)\b|\be\.g\.',
        quote, re.I,
    ) is not None


def publication_row_patterns(rows):
    ids = "|".join(re.escape(row) for row in sorted(rows, key=lambda row: (-len(row), row)))
    row_id = rf"(?<![A-Za-z0-9_-])(?:{ids})(?![A-Za-z0-9_-])"
    row_item = rf"(?:第\s*)?{row_id}(?:\s*(?:行|项|条))?"
    all_rows = r"(?:全部(?:行|条目)?|所有行|(?i:\ball rows\b))"
    choice = rf"(?P<items>{all_rows}|{row_item}(?:\s*(?:、|和|与|及|(?i:\band\b))\s*{row_item})*)"
    return row_id, all_rows, choice


PUBLICATION_DELAY = (
    r"(?:(?:暂(?:时)?|目前|现在|眼下|先)\s*)?(?:不要|不再|不|别)\s*"
    r"(?:(?:马上|立刻|现在|对外)\s*)?(?:上传|投稿|发布|公开|提交|发(?:出|送|表)?)|"
    r"(?:只|先|暂(?:时)?)\s*(?:留(?:在)?|保留在?)\s*本地(?:保存)?"
)
PUBLICATION_TOPIC = r"(?:(?:的\s*)?(?:投稿|上传|发布|公开稿|内容|原文)\s*)?"
PUBLICATION_QUALIFIER = r"(?:(?:但是?|不过|只是|然而)\s*)?"


def explicitly_approved_rows(quote, rows):
    """Interpret direct grants conservatively. Ambiguous language grants nothing."""
    if not rows or hypothetical_publication_reply(quote):
        return set()

    row_id, all_rows, choice = publication_row_patterns(rows)
    prefix = r"(?:我|本人)?\s*(?:(?:本批|这批|这一批|本次|这次)(?:中)?)?\s*(?:我|本人)?\s*(?:明确\s*)?(?:只|仅)?\s*"
    consent = r"(?:同意|批准|允许|授权)"
    publish = r"(?:上传|投稿|对外公开|公开发布|公开|发布)"
    displayed_terms = r"按(?:本批表|本表|表)(?:中)?(?:的)?(?:署名(?:、|和|与|及)许可|许可(?:、|和|与|及)署名)"
    english_consent = r"(?i:(?:I\s+)?(?:only\s+)?(?:approve|authorize))"
    english_publish = r"(?i:upload(?:ing)?|publish(?:ing)?|submit|submitting|publication|submission)"
    direct_grants = tuple(re.compile(pattern) for pattern in (
        rf"{prefix}{consent}\s*(?:将|把)?\s*{choice}\s*(?:{displayed_terms}\s*)?{publish}",
        rf"{prefix}{consent}\s*{publish}\s*{choice}",
        rf"{prefix}{choice}\s*(?:同意(?:观点|内容|原文)\s*(?:、|且|并)\s*)?{consent}\s*{publish}",
        rf"{english_consent}\s+{choice}\s+(?i:for)\s+{english_publish}",
        rf"{english_consent}\s+(?i:(?:the\s+)?){english_publish}\s+(?i:(?:of\s+)?){choice}",
    ))
    # The only split grant is an adjacent instruction to use the displayed table's terms.
    row_consent = re.compile(rf"{prefix}{consent}\s*{choice}")
    follow_displayed_terms = re.compile(rf"{displayed_terms}\s*{publish}")
    content_consent = re.compile(rf"{prefix}{consent}\s*{choice}\s*的\s*(?:观点|内容|原文)")
    courtesy = re.compile(r"(?:好(?:的)?|明白(?:了)?|收到(?:了)?|谢(?:谢(?:你|您)?|了)|(?i:ok(?:ay)?|thanks|thank you))")

    denial = (
        r"不(?:同意|批准|允许|授权)|(?:尚|还)?未(?:同意|批准|允许|授权)|没(?:有)?(?:同意|批准|允许|授权)|"
        rf"先别|先不|暂不|不要|不能|禁止|退回|撤回|作废|暂缓|另议|待定|{PUBLICATION_DELAY}"
    )
    defer = (
        r"(?:下次|下轮|下一轮|以后|之后|改完|审完|核完|确认后|稍后|待).*?再|"
        r"再(?:上传|投稿|发布|公开|决定|确认|议|发)|先(?:等|确认|审查|审核|核对|核实|准备|沟通|放着|搁置)"
    )
    english_hold = r"(?i:\b(?:not|don't|reject|wait|until|defer|revoke|withdraw|pending|on hold|hold off)\b)"
    hold = re.compile(rf"{denial}|{defer}|{english_hold}")
    unscoped_hold = re.compile(
        rf"^{PUBLICATION_QUALIFIER}(?:先等|等|待|审完|改完|确认后|"
        r"(?i:(?:(?:but|however)\s+)?(?:wait|until|after|once)\b))"
    )
    scoped_holds = tuple(re.compile(pattern) for pattern in (
        rf"{PUBLICATION_QUALIFIER}{choice}\s*{PUBLICATION_TOPIC}(?:{denial}|{defer}|(?i:is\s+)?{english_hold}|等|待).*",
        rf"{PUBLICATION_QUALIFIER}(?:我\s*)?(?:{denial})\s*(?:{publish}\s*)?{choice}(?:\s*{publish})?",
        rf"(?i:(?:do not|don't)\s+){english_publish}\s+{choice}",
    ))

    def selected(choice_text):
        return set(rows) if re.fullmatch(all_rows, choice_text) else set(re.findall(row_id, choice_text))

    def matched_rows(patterns, clause):
        for pattern in patterns:
            match = pattern.fullmatch(clause)
            if match:
                return selected(match["items"])
        return set()

    granted, vetoed = set(), set()
    for sentence in re.split(r"[。.!！;；\n]", quote):
        previous = ""
        for clause in (part.strip() for part in re.split(r"[,，]", sentence)):
            if unscoped_hold.search(clause):
                vetoed.update(rows)
            elif hold.search(clause):
                vetoed.update(matched_rows(scoped_holds, clause) or rows)
            elif follow_displayed_terms.fullmatch(clause):
                granted.update(matched_rows((row_consent,), previous))
            elif clause:
                direct = matched_rows(direct_grants, clause)
                if direct:
                    granted.update(direct)
                elif not any(pattern.fullmatch(clause) for pattern in (courtesy, content_consent, row_consent)):
                    # An unrecognized qualifier may narrow an earlier grant.
                    vetoed.update(rows)
            previous = clause
    return granted - vetoed


def withdraw_upload_grants(state, root, message_ref, message):
    batch = state["batch"]
    grants = batch["authorizations"]
    quote = message["user_quote"]
    if not grants or hypothetical_publication_reply(quote):
        return

    row_id, all_rows, choice = publication_row_patterns(batch["rows"])
    publish = r"(?:上传|投稿|公开|发布)"
    withdrawal = r"(?:撤回|取消|收回)\s*"
    permit = rf"(?:对外)?{publish}?(?:授权|许可|批准)"
    suspension = rf"(?:{PUBLICATION_DELAY}|暂(?:时)?(?:缓|停)(?:对外)?{publish})"
    patterns = tuple(re.compile(pattern) for pattern in (
        rf"(?:我|本人)?\s*{withdrawal}(?:本批\s*)?(?:对\s*)?{choice}\s*(?:的\s*)?{permit}",
        rf"{choice}\s*(?:不再允许|不同意|不允许|不要|禁止)\s*(?:对外)?{publish}",
        rf"(?:我|本人)?\s*(?:不再允许|不同意|不允许|不要|禁止)\s*{choice}\s*(?:对外)?{publish}",
        rf"(?i:(?:I\s+)?(?:revoke|withdraw)\s+approval\s+for\s+){choice}",
        rf"{PUBLICATION_QUALIFIER}{choice}\s*{PUBLICATION_TOPIC}{suspension}(?:了|吧)?",
        rf"{PUBLICATION_QUALIFIER}{suspension}\s*{choice}(?:了|吧)?",
    ))
    unscoped_delay = re.compile(rf"{PUBLICATION_QUALIFIER}{suspension}(?:了|吧)?")
    withdrawn = set()
    for part in re.split(r"[,，。.!！;；\n]", quote):
        clause = part.strip()
        if unscoped_delay.fullmatch(clause):
            withdrawn.update(grants)
            continue
        for pattern in patterns:
            match = pattern.fullmatch(clause)
            if match:
                selected = match["items"]
                withdrawn.update(grants if re.fullmatch(all_rows, selected) else re.findall(row_id, selected))
                break
    for selected in sorted(withdrawn & grants.keys()):
        grant = grants[selected]
        later_message(message, user_message(root, grant["message_ref"]),
                      "The user withdrawal must follow that row's approval in the same conversation")
        state.setdefault("upload_withdrawals", []).append({
            "task_revision": state["task_revision"], "batch_id": batch["id"], "row_id": selected,
            "message_ref": message_ref, "grant": grants.pop(selected),
        })


def require_after_withdrawal(state, root, row_id, user):
    for withdrawal in reversed(state.get("upload_withdrawals", [])):
        if (withdrawal["task_revision"], withdrawal["batch_id"], withdrawal["row_id"]) == (
            state["task_revision"], state["batch"]["id"], row_id
        ):
            later_message(user, user_message(root, withdrawal["message_ref"]),
                          "A new user approval must follow the withdrawal in the same conversation")
            return


def verify_upload_grant(state, root, row_id, grant):
    batch = state["batch"]
    row = batch["rows"][row_id]
    require(isinstance(grant, dict) and grant.get("presentation") is not None,
            "The historical grant lacks a bound presentation")
    require(grant["row_sha256"] == canonical_sha(row), "The upload row changed")
    text_ref(root, row["public_ref"], suffixes=(".md",))
    if grant["batch_sha256"] == batch["sha256"]:
        require(grant["presentation"] == batch.get("presentation"), "The grant has a different presentation")
        table, displayed = read_presentation(root, grant["presentation"])
        require(table == state["upload_table_markdown"], "The grant lacks the exact displayed table")
    else:
        table, displayed = read_presentation(root, grant["presentation"])
        old_rows = {row_id: row}
        rendered_row = proposed_table({**batch, "rows": old_rows}, root).splitlines()[-1]
        require(table.startswith(f'# 拟上传表 {batch["id"]} 第 ') and rendered_row in table.splitlines(),
                "The originally displayed batch does not cover this unchanged row")

    quote_ref = grant["message_ref"]
    user = user_message(root, quote_ref)
    prior = state["publication_approval_messages"].get(user["source_message_id"])
    require(grant["source_message_id"] == user["source_message_id"]
            and prior == {"message_sha256": quote_ref["sha256"], "batch_sha256": grant["batch_sha256"]},
            "The grant does not identify the recorded user approval for this batch")
    closure = user_message(root, state["closure_message_ref"])
    later_message(displayed, closure, "The original display must follow this revision's closure")
    later_message(user, displayed, "The original user approval must follow the display in the same conversation")
    require_after_withdrawal(state, root, row_id, user)
    shown_ids = set(re.findall(r"^\| ([A-Za-z0-9_-]+) \|", table, re.M))
    require(row_id in explicitly_approved_rows(user["user_quote"], shown_ids),
            "The original user message does not authorize publication of this row")


def effective_closure(state, root):
    if not state or state.get("status") not in {"RETROSPECTIVE_REQUIRED", "RETROSPECTIVE_RECORDED"}:
        return state
    try:
        original = user_message(root, state["closure_message_ref"])
        event = state["closure_event"]
        require(all(event[key] == original[key] for key in ("actor", "user_quote", "source_message_id", "source_locator"))
                and event["task_id"] == state["task_id"] and event["task_revision"] == state["task_revision"]
                and event["contains_change_request"] is False and closure_checker()(original["user_quote"]),
                "The close event must match this revision and the original explicit user reply")
        require_current_closure_order(root, state, original)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        view = copy.deepcopy(state)
        historical = {"task_revision": view["task_revision"], "reason": str(exc),
                      "delivery_message_ref": view.get("delivery_message_ref")}
        for key in ("closure_event", "closure_message_ref", "retrospective", "upload_table_markdown", "batch"):
            if key in view:
                historical[key] = view.pop(key)
        view.setdefault("legacy_unverified_closures", []).append(historical)
        view["batch"] = None
        view["status"] = "DELIVERED_AWAITING_FEEDBACK"
        return view
    return state


def effective_upload_authorizations(state, root):
    """Expose a verified current closure and grants while retaining historical evidence."""
    state = effective_closure(state, root)
    batch = state.get("batch") if state else None
    if not batch or not batch.get("authorizations"):
        return state
    rejected = {}
    for row_id, grant in batch["authorizations"].items():
        try:
            verify_upload_grant(state, root, row_id, grant)
        except (KeyError, OSError, TypeError, ValueError) as exc:
            rejected[row_id] = str(exc)
    if not rejected:
        return state

    view = copy.deepcopy(state)
    audit = view.setdefault("legacy_unverified_authorizations", [])
    for row_id, reason in rejected.items():
        grant = view["batch"]["authorizations"].pop(row_id)
        entry = {"task_revision": view["task_revision"], "batch_id": batch["id"],
                 "row_id": row_id, "reason": reason, "grant": grant}
        if entry not in audit:
            audit.append(entry)
    return view


def inspect_closeout(request, evidence_root):
    root = Path(evidence_root).resolve()
    state = json_ref(root, request["previous_ref"]) if "previous_ref" in request else None
    return transition(request, state, root)


def transition(request, state, root):
    """Validate a single transition against a caller-selected immutable state."""
    operation, task, rev = (request.get(key) for key in ("operation", "task_id", "task_revision"))
    require(text(task) and type(rev) is int and rev > 0, "Bind the current task and positive integer revision")
    state = copy.deepcopy(state)
    if state is not None:
        require(state["schema"] == STATE_SCHEMA and state["task_id"] == task, "The prior local receipt belongs to another task")
    state = effective_upload_authorizations(state, root)
    if operation == "delivery":
        if state is not None and state.get("status") == "DELIVERY_QUESTION_MISSING":
            state = None
        result = delivery(request, state, root)
        for field in ("legacy_unverified_closures", "legacy_unverified_authorizations", "upload_withdrawals"):
            if state is not None and state.get(field):
                result[field] = state[field]
        return result
    require(state is not None and state["task_revision"] == rev, "The prior local receipt must bind this revision")
    actions = {"delivery_sent": delivery_sent, "reply": reply, "retrospective": retrospective,
               "batch_presented": batch_presented, "approve_upload": approve_upload}
    require(operation in actions, "Unknown closeout operation")
    return actions[operation](request, state, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    entry = parser.add_mutually_exclusive_group(required=True)
    entry.add_argument("--schema", action="store_true")
    entry.add_argument("--request", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.schema:
            result = schema()
        else:
            root = (args.evidence_root or args.request.resolve().parent).resolve()
            from tools.task_closeout_history import advance_closeout

            result = advance_closeout(json.loads(args.request.read_text(encoding="utf-8-sig")), root)
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            require(not args.request or args.output.resolve().is_relative_to(root), "Keep the receipt beneath the evidence root")
            with args.output.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(output)
        else:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            print(output, end="")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "ACTION_REQUIRED", "detail": str(exc)}, ensure_ascii=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
