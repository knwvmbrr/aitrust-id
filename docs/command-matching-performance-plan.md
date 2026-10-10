# Command matching performance repair

The context-v5 evaluator is slow on repeated non-matching download tokens: about
99 ms at 20,000 characters, 2.57 seconds at 100,000, and over the four-second
subprocess observation limit at 200,000 on the current Mac. No remote request or
downloaded command was executed. This is a repeatability/availability issue, not
new independent accuracy evidence.

Plan before refactor:

1. Isolate the regex and context costs on bounded synthetic inputs. Identify
   repeated rescanning rather than raising the timeout or shrinking the declared
   input limit silently.
2. Scan command delimiters once and evaluate a pipe candidate only where a
   supported shell receives that pipe. Preserve full-text offsets, stdout routing,
   literal-display and warning checks. Explicitly treat unsupported multiline
   forms as outside the bounded matcher, without a safety-clearance claim.
3. Measure dense positive, literal-display, warning and substitution forms too;
   a fast negative path alone is insufficient. Remove repeated full-prefix
   scans if those measurements show the same problem.
4. Any changed detection behavior gets a new signal version, with older IDs and
   the exact prior source retained. Keep PS as the adopted tag; UC/SC/BT adoption
   and all independent release requirements remain unchanged. Update the exact
   device projection, explanations, source catalogue and measured records.
5. Execute positive/negative and differential regressions, declared-hardware
   long-input timing, cross-engine device parity and actual service checks. A
   timeout or changed claim must remain a failure, not a passing measurement.

Risks: a delimiter optimization can alter quotes, line boundaries or offsets;
the projected browser method can diverge; new IDs can lose user explanations;
development timing can be misread as a population accuracy guarantee. Mitigation
is explicit versioning, literal/streaming/Unicode boundary cases, exact source
identity, real projection parity, and separate accuracy gates. No new public
endpoint, model download, training collection or local Docker launch is needed.

Cross-engine execution found a word-boundary difference for post-Unicode-15
letters directly beside ASCII command names. Before changing the method, extend
the plan: freeze the regex word-character class to Python 3.12's Unicode 15
letters/numbers/underscore, replace command word boundaries with that explicit
class, and project the same source. Generate the class from the named Unicode-15
interpreter, preserve its digest, and verify every Unicode scalar against that
reference. This preserves the existing server interpretation while making the
browser repeat it. It is not a universal shell parser: later Unicode assignments
and surrounding prose still require independent false-positive assessment.
