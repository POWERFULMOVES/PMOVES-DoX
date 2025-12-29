// Example Google Mangle program for PMOVES_DoX tag normalization.
// Usage: pass this file as `mangle_file` and set `mangle_exec=true`.

// EDB predicate expected from backend (facts generated from extracted tags):
//   tag_raw("Loan Servicing").

// Synonyms and canonical forms
canon("Loan Servicing", "Loan Servicing").
canon("Servicing", "Loan Servicing").
canon("Underwriting", "Underwriting").
canon("UW", "Underwriting").
canon("Loan Origination", "Loan Origination").
canon("Origination", "Loan Origination").
canon("RulesEngine", "Rules Engine").

// Normalize a raw tag to its canonical form
normalized_tag(Tcanon) :- tag_raw(Traw), canon(Traw, Tcanon).

// If no synonym is found, fall back to the raw value
normalized_tag(Traw) :- tag_raw(Traw), not canon(Traw, _).

