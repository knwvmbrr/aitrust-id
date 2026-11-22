# Consume actual automated evidence in the accessibility release gate

Before changing CI, preserve the existing assessor, actual-human criteria and
failure exit. The gate currently reads default eval/release paths that this repo
does not publish, so it reports missing automation even when committed current
website/extension receipts exist. Resolve only the two explicit flat runs/ JSON
paths from state.current_engineering_revalidation, refuse nonregular/link paths,
and pass them to the existing assessor. It must still reject missing/stale/failed
receipts and require the same real NVDA/VoiceOver reviews. No threshold, identity
or manual-attestation rule changes; statistical release assessment still runs
with always(). Record actual assessment after the complete current source freeze.
