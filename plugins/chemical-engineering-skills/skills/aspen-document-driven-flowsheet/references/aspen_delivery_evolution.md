# Aspen Delivery, Packaging, And Evolution

Use this reference when handing off final Aspen files, producing synchronized
Markdown/LaTeX/PDF notes, building a portable package, or promoting reusable
lessons back into the skill.

## Delivery Documents

- Keep Markdown source, LaTeX source, and PDF synchronized.
- Compile LaTeX with XeLaTeX twice for Chinese/Unicode projects.
- Verify page count, extracted text, rendered pages, and key claims against the
  latest Aspen outputs.
- If the user asks for a process/package explanation as PDF, deliver the
  explanation as a rendered and text-checked PDF, not only Markdown.
- If the user asks for PDF-only delivery text, treat all human-readable Markdown,
  TXT, DOCX, and TEX files as build artifacts, not shipped artifacts. Keep them
  outside the final package or delete them after PDF generation.
- For Chinese or other non-ASCII text on Windows, prefer XeLaTeX/ctex or a
  Unicode-safe source file. Inline PowerShell/Python here-strings can silently
  replace characters with `?`; do not trust the generator until both `pdftotext`
  and rendered PNG pages show readable text.
- Treat generated delivery claims as untrusted until final audit commands check
  the latest exported input, block CSV, stream CSV, and PDF text.
- If historical branches or diagnostic sweeps can be mistaken for active model
  truth, rewrite the front matter around current authority, current hard gate,
  evidence index, and historical-only labels.

## Portable Production Package

A production package must be runnable after unzip on another Windows Aspen
machine. Include:

- Package-root entrypoints for verify, environment check, skill install, case
  audit, generic Aspen COM run, project initialization, manifest generation, and
  repackaging.
- Generic config templates for goals, hard gates, molecular weights, product
  targets, recycle targets, forbidden block types, temperature sanity,
  thermodynamic zoning, and authority manifests.
- Relative package manifest paths. Do not leave local absolute paths as
  authority.
- Labels that separate project-specific examples from reusable tools.
- Verification from the package root before handoff.
- Zip/extract smoke test before handoff. Run the package verifier from the
  extracted copy, check extension inventory, and remove render/test artifacts
  such as `_qa_*`, `_render_*`, or one-off font/PDF probes before packaging.
- Exact quick-start commands in the README when a README is part of the requested
  package.

## Text Generation Failure Gate

Use this gate whenever delivery text is part of the package:

1. Generate the human entry document from current authority, audit JSON, stream
   CSV, block CSV, and source ledger, not from memory or stale branch notes.
2. Render the PDF to PNG with `pdftoppm` and inspect at least the entry page plus
   pages containing tables, Chinese text, equations, or PFD labels.
3. Extract text with `pdftotext -enc UTF-8` or `pypdf` and search for `????`,
   replacement characters, stale branch labels, old stream names, and broken
   numbers.
4. If the visual layer or text layer fails, fix the generation route before
   packaging. Do not call a PDF valid because the file opens.
5. Enforce the requested artifact policy in the verifier: PDF-only text means no
   `.md`, `.txt`, `.docx`, or `.tex`; synchronized-source delivery means the
   source files must exist and match the rendered PDF.

## Self-Evolution Mechanism

Use the current `self_evolution_protocol.md` and the chemical expert's
`STRICT_ACCEPTANCE_AND_LEARNING.md`. Logging a correction or completing a
project is not learning eligibility. Audit failing islands and major corrections
locally; do not infer a shared default from them. Canonical candidate generation requires
the user's explicit current-task/revision closure and independently verified
strict evidence with a hash-bound complete lineage. At every delivery ask
whether the task is finished or needs improvement; do not start canonical promotion while
adjustments remain. The central EVOLUTION_LOOP.md distinguishes macro prompt
principles from data-pattern hypotheses and chooses one existing Skill owner.
Case-local relaxation, unassessed legacy sources and their descendants remain
audit-only; a user-accepted blocker or later success label cannot clear that gate.

Authorized temporary submission follows the expert's
[inbox route](../../chemical-engineering-expert/references/EXPERIENCE_INBOX.md),
including during an active task. User-requested periodic consolidation still
uses the existing closure, lineage and quality gates below for formal promotion.

1. Capture the failure or improvement as a short lesson.
   Include what went wrong, the concrete fix, and the artifact that proves it:
   source document section, generated `.inp`, Aspen status CSV, stream CSV,
   rendered PDF, package manifest, or command output.

2. Classify the lesson.
   Use categories such as document-extraction, kinetics, unit-conversion,
   recycle, pressure, separator, convergence, delivery, packaging, or
   skill-routing.

3. Filter before promotion.
   Promote only stable process rules, audit commands, and known Aspen failure
   modes. Do not promote a project route, case-specific stream ID, one-off
   separator split, pressure value, or kinetic constant as a general rule.

4. Request governed candidate review only after the central lineage check.
   Use the installed script with an explicit project directory and the exact
   candidate artifact named in the lineage manifest. This example is a CLI
   shape, not a supplied valid manifest:

```powershell
python <installed-docflow>/scripts/self_evolve_skill.py `
  --project-name <project> `
  --project-dir <project-directory> `
  --lesson-file <root-candidate.json> `
  --lineage-manifest <strict-lineage.json>
```

The default output is `<project-directory>/aspen_case_audit/evolution`; an
explicit `--output-dir` must also be project-local. Skill/plugin/archive output
locations are prohibited. The production evaluator is resolved from the installed
chemical-expert skill, not the working directory. `--eligibility-module` is an
explicit reviewed-module override for isolated integration tests, not an
automatic discovery route.

Missing/invalid lineage, a relaxed ancestor, legacy origin, evidence hash drift,
or a lesson not bound to the manifest's root artifact returns exit code `2` and
only `case_audit_only` records: no candidate patch. Eligible strict input returns
`0` and project-local candidate-review JSON/Markdown plus a patch. Both paths
keep `default_retrieval=false` and `canonical_write_authorized=false`. Script
success is candidate-review admission, not canonical promotion or delivery.

5. Review without automatic merge.
   Compare the candidate against the existing owner and keep only the project
   audit when already covered. A genuine reusable delta still needs the central
   promotion/review authority and validation before any canonical edit. Neither
   this checklist nor a generated patch grants that authority.

## Output Standard

Keep outputs actionable: cite document evidence, state Aspen implementation,
list open assumptions, and name the next verification action. If the model
cannot be completed, stop at the smallest faithful Aspen draft plus a blocker
list tied to document evidence. For final deliverables, follow the requested
artifact policy: synchronized-source deliveries include source text plus PDF,
while PDF-only deliveries ship the human-readable text only as PDF beside Aspen
files and machine-readable audits. Always mention PDF validation status.
