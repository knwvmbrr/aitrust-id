# Local reference corpus

Architecture: keep reference documents separate from the evaluator and its
ephemeral request bodies. The owner explicitly chooses plain UTF-8 text files
and a private corpus file outside the checkout. Import exact bytes, record their
SHA-256, and assign stable document IDs. A manifest hash binds the ordered source
records and the corpus version. Queries use normalized Unicode text, returning
literal matching passages with both query and source code-point spans. No model,
network connection, HTML rendering, shell execution or automatic upload occurs.

This reference store is deliberately persistent, user-controlled material. It
does not change the services' no-content-persistence contract. Sensitive source
text stays in the private corpus; users should attach only material they have
permission to use. Checksums detect accidental modification; they do not prove
who wrote a document or that its statements are true.

Risk controls: reject symbolic links, non-regular inputs, invalid UTF-8, duplicate
source identities, oversized inputs and unsafe corpus permissions. Create the
corpus exclusively at mode 0600 in an owner-only directory. Verify the complete
manifest on every query. Reject corrupted content instead of returning partial
matches. Bound imports to 32 documents, 200,000 characters per document and
2,000,000 bytes total; bound queries to 2,000 characters and ten matches.

The first workflow supports `.txt` and `.md` files as passive text. It does not
extract PDF, image, audio or video content. No semantic truth, contradiction,
provenance, or NF/FI assertion is issued by a literal reference match. The corpus
attachment requirement and future retrieval/classification requirements have
separate acceptance.

Use Python 3.10 or later; no extra packages are required:

```sh
python3 scripts/corpus.py create --output ~/.local/share/aitrust-id/reference.json \
  --source handbook=./handbook.txt --source notes=./notes.md
python3 scripts/corpus.py query --corpus ~/.local/share/aitrust-id/reference.json \
  --text 'a passage to find'
python3 scripts/corpus.py inspect --corpus ~/.local/share/aitrust-id/reference.json
```

The output reports `REFERENCE_MATCH` or `NO_REFERENCE_MATCH`. It never says the
answer is verified. Delete the private corpus file to remove its stored text.
Creating a new version requires a new output path; existing corpora are not
silently overwritten. Source paths are not stored in the exported manifest.

For private queries, use `--stdin` instead of `--text`, so the phrase is not in
process arguments or shell history. Query results intentionally include the
matched passage. Do not forward them automatically to public issue reports.
