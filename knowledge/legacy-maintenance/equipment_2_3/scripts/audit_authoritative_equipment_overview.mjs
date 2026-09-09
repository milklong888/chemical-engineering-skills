import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";


function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (key === "--input" || key === "--output") {
      result[key.slice(2)] = argv[index + 1];
      index += 1;
    }
  }
  if (!result.input || !result.output) {
    throw new Error("usage: node audit_authoritative_equipment_overview.mjs --input <xlsx> --output <json>");
  }
  return result;
}


const args = parseArgs(process.argv.slice(2));
const inputPath = path.resolve(args.input);
const outputPath = path.resolve(args.output);
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheets = [];

for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange(true);
  const address = used?.address ?? null;
  const values = address ? used.values : [];
  const formulas = address ? used.formulas : [];
  const inspection = address
    ? await workbook.inspect({
        kind: "region,table",
        sheetId: sheet.name,
        range: address,
        maxChars: 20000,
        tableMaxRows: 100,
        tableMaxCols: 40,
        tableMaxCellChars: 200,
      })
    : null;
  sheets.push({
    name: sheet.name,
    used_range: address,
    values,
    formulas,
    inspection_ndjson: inspection?.ndjson ?? "",
  });
}

const result = {
  schema: "authoritative-equipment-overview-workbook-audit-v1",
  source_path: inputPath,
  sheet_count: sheets.length,
  sheets,
};
await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
process.stdout.write(`${JSON.stringify({ status: "PASS", output: outputPath, sheet_count: sheets.length })}\n`);
