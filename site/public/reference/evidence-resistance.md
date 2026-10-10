# Current evidence resistance

The executable assessment is `scripts/assess-evidence-resistance.py`; its dated
observations are in `runs/2026-10-10-evidence-resistance.json`. It inventories all
38 signal versions and separates active measurements, inactive proposals and
unmeasured redactor coverage. It does not rank hypothetical classes as proven.

For the four current shell methods, eight synthetic spellings pass Bash syntax
validation (`bash -n`, no execution) and agree under Python shlex tokenization.
Every one evades the bounded lexical matcher. A one-character escape suffices
in the tested forms; quoting a command fragment takes two inserted characters.
These are upper bounds on the smallest observed textual evasion in these trials,
not a money/time cost, population failure rate, or proof of runtime equivalence
across all shells and environments. The encoded-payload method separately misses
an aliased decoder; that experiment does not establish execution equivalence.

The redactor recognizes selected patterns and can miss novel or sensitive input.
No recognizer attack prevalence was measured. Successful redaction is not
anonymity. Current assertions are unsigned: a subject hash binds content bytes
but authenticates neither an issuer nor a claim. Consumers refuse signed records
they cannot verify. Research credential interpretation consumes supplied status
codes and is not a working manifest/signature/OCSP adapter.

Inactive signal versions and proposed provenance methods have no measured attack
resistance. A future implemented method must supply its own threat assumptions,
attack observations and accuracy evidence. This functioning assessment closes
the assessment job for the actual current methods; it releases no detector,
receipt or future method and does not close their independent gates.

Rerun after source or signal catalogue changes:

```sh
python3 scripts/assess-evidence-resistance.py --output output/verification/evidence-resistance.json
```

The report checks source stability and never includes real submitted text.
All trial URLs are synthetic and no network request or submitted command runs.
