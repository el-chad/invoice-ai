# Synthetic invoice fixtures

All suppliers and invoices are fictional. Each JSON is the ground truth for its
paired text document, including explicit nulls for absent fields.

- `correct`: a complete, consistent single-item invoice.
- `missing_fields`: supplier and due date are absent from the text and null in JSON.
- `incorrect_field`: the source prints total 119.00 despite subtotal 180.00 and tax
  11.00. The JSON faithfully preserves the printed total, without correcting it.
- `multiple_items`: a complete invoice containing three line items.

All four ground-truth JSONs validate against Invoice. Schema validation does not
check arithmetic consistency. These fixtures and tests make no network calls.
