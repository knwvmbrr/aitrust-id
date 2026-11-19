# Authority phrases in supported quotation context

The existing authority method finds expertise phrases and source markers in a
literal sentence unit. It records `The training example says "Experts agree".`
as an unmarked authority finding. It also borrows the URL from `Experts agree;
the quoted example is "https://example.invalid".` to mark the opening phrase.

Add a separately versioned candidate, `ascii-quoted-authority-observations/1.0.0`,
with its own callable module and CLI. It reuses the existing English selection,
frozen NFC normalization, authority phrase/source-marker regexes and literal
sentence units. Parse balanced ASCII double quotes over the selected subject.
Record every phrase in its unit with an explicit supported-quote context. Keep
quoted phrases visible in a separate list. Nominate only phrases outside those
quotes which lack a same-unit source marker outside those quotes. A source in a
separate quotation cannot supply the association.

A quoted phrase can itself contain a marker, and both locations are retained.
The candidate does not decide who endorses a quote. Quotes can express endorsed
claims, irony, dialogue, examples or titles. Single quotes are ordinary characters
in this narrow grammar. Curly double quotes, guillemets, backticks, escaped ASCII
quotes and unbalanced quotes yield Unavailable. No malformed quotation is silently
closed at the end of the subject. Sentence units remain the published lexical
units, with their existing punctuation limitations.

Reuse the established input bound of 8,000 normalized characters and 32,000 UTF-8
bytes. Bound candidate quotes, phrases, units and source markers and refuse excess.
The brief output carries counts and fixed method/limit fields. Optional private
details carry exact phrase/unit/quote/marker spans, normalized subject identity
and source fingerprints. Neither output copies the subject. Use the existing
owner-private new-directory writer. No network, model or service is required.

The existing MT workers retain their current imports and method contracts.
Verify the candidate's optional import failure leaves ordinary urgency and
authority operation usable. Exercise actual CLI before/after controls, preserved
legacy behavior, exact normalized spans, malformed forms, resource bounds and
private export refusal. Use synthetic examples and publish measured control
results without accuracy, independence, intent or MT-release claims.
