# DataCleaner — version 1 contract

DataCleaner accepts a customer sheet with `name`, `email`, `phone`, and `birth_date` columns. It returns `clean_customers.csv`, `errors.csv`, and a summary. The fictional sheet in `examples/` defines the expected behavior for implementation and tests.

## Input

- Accept UTF-8 `.csv` files (optional BOM, comma delimiter) and `.xlsx` files (first worksheet). The first row is the header. It must contain the four exact column names, in any order. Missing, repeated, or additional columns are rejected.
- In XLSX files, accept text and Excel date cells. A formula in a data cell rejects that row. All CSV cells are text.
- Completely empty rows do not count toward processing or the summary. `source_row` is the physical row number, with the header on row 1. A CSV row with the wrong number of cells produces `INVALID_ROW`, with `column` set to `row` and `original_value` containing a JSON array of its cells.
- Version 1 limits each file to 5 MB and 10,000 data rows. An empty file, invalid header, unreadable format or encoding, or exceeded limit produces a file-level error before row-level results are returned.

## Fields and automatic corrections

| Column | Required | Automatic correction | Row error |
| --- | --- | --- | --- |
| `name` | Yes | Trim outer whitespace, collapse repeated inner whitespace, and capitalize each word. The particles `de`, `da`, `do`, `das`, and `dos` remain lowercase unless they are the first word. | Empty after cleanup. |
| `email` | Yes | Trim outer whitespace and convert to lowercase. | Empty, contains inner whitespace, or has invalid syntax. The supported syntax has a local part without leading, trailing, or consecutive periods; one `@`; and a domain with at least one period and alphanumeric labels (interior hyphens allowed). Quoted addresses and internationalized domains are outside this version. Mailbox existence is not checked. |
| `phone` | No | Remove spaces and punctuation. Accept 10 or 11 Brazilian national digits with a two-digit area code from 11 to 99, optionally preceded by `55` or `+55`. Export `+55` followed by the 10 or 11 national digits. An empty value stays empty. | A filled value contains letters, another country code, an area code outside the range, or the wrong number of digits. The area code is never inferred, and number existence is not checked. |
| `birth_date` | No | Accept `DD/MM/YYYY`, `YYYY-MM-DD`, or an Excel date cell. Export `YYYY-MM-DD`. An empty value stays empty. | A filled value is not a real date or falls after the processing date. The engine does not swap month and day or repair impossible dates. |

Name capitalization may not preserve personal spelling such as `McDonald` or acronyms. Version 1 does not restore accents, correct names, verify phone numbers, or apply national ID or age rules.

## Duplicates and row outcomes

1. Validate and normalize all four fields. Record every issue in a row, in the column order shown above.
2. A row with any field error is **invalid** and appears only in `errors.csv`. Its email does not reserve a duplicate key.
3. For a row without field errors, compare the normalized email with earlier valid rows. The first occurrence is **valid** and appears in `clean_customers.csv`. Later occurrences are **duplicates** and appear only in `errors.csv`, with the first accepted row number in the reason.
4. Do not merge duplicate rows or discard a row without recording its rejection.

The categories are exclusive: `received = valid + invalid + duplicate`. `received` counts nonempty data rows. `invalid` and `duplicate` count **rows**; `errors.csv` has one entry per issue, so it may have more entries than the combined rejected row count.

## Outputs

- `clean_customers.csv`: UTF-8, header `name,email,phone,birth_date`, one row per accepted customer in source order.
- `errors.csv`: UTF-8, header `source_row,column,original_value,code,message`. `original_value` preserves the source value of the affected cell; for duplicates, it contains the original email. `message` explains the issue for a human reviewer. Entries follow source order and, within a row, column order.
- API summary: `received`, `valid`, `invalid`, and `duplicate`. The example includes `examples/expected_summary.json`.

Version 1 error codes are `REQUIRED`, `INVALID_EMAIL`, `INVALID_PHONE`, `INVALID_DATE`, `FUTURE_DATE`, `DUPLICATE_EMAIL`, `FORMULA_NOT_ALLOWED`, and `INVALID_ROW`. Codes are stable integration identifiers. Messages may be improved without breaking integrations that use the codes.

## Example acceptance criteria

`examples/sample_customers.csv` and `examples/sample_customers.xlsx` contain the same 18 customer records. The expected result has 8 valid rows, 8 invalid rows, 2 duplicates, and 11 entries in `examples/expected_errors.csv`. Processing preserves source order and physical row numbers.
