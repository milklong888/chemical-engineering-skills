# Minimal Project Start

Use this folder to see what must be filled before promoting an Aspen case.

Minimum cold-start steps:

1. Put current PDFs, DOCX files, spreadsheets, and Aspen exports in
   `source_docs/`.
2. Fill `authority_manifest.example.json` with the current source basis and
   active hard gates.
3. Fill `project_config.example.json` with only gates that can be proven from
   the current project.
4. Build the first scaffold with provisional labels, then replace one reactor
   or separation island at a time.
5. Promote only the newest case whose exported input, block CSV, stream CSV,
   status text, and delivery note pass the named gates.

Do not begin from old cases. Use old cases only after the current document
route and hard gates are locked.
