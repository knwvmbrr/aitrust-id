# Pinned SDK loading — repair architecture

An isolated copy of the published source reproduced a namespace collision:
the wrapper/native files passed their installed-distribution checks, but the
worker's ordinary `import c2pa` loaded a same-named folder in the checkout.
A harmless marker established execution; no real content or network was used.
The worker failed unavailable rather than producing a false verdict, but the
claim that it used the checked wrapper was not reliable in that situation.

Load the checked initializer by its absolute distribution path, with that exact
package directory as its relative-import search location. Refuse any preloaded
`c2pa` module. Remove checkout and current-directory entries from the child's
search path while importing the SDK, and retain that restricted path for its
reader lifetime. Keep the parent free of native imports. Existing settings,
limits, PNG boundary and output/privacy behavior stay in place.

Retain the exact checked distribution's site-packages root even when the user's
virtual environment lives inside the checkout. The wrapper resolves its own
version from distribution metadata. A real copied `.venv` control verifies this
alongside the package/file-shadow refusals; other checkout entries stay excluded.

Test source-tree package and single-file collisions in private copied checkouts,
then repeat the real signed, changed and unsigned PNG controls on Mac and
network-isolated Linux. Unit controls cover preloaded modules and cleanup after
initializer failure. Hosted native runs and published-source acceptance must be
fresh for the changed source; historical parser evidence is not substituted.

This mitigates namespace collisions. It is not protection against a compromised
Python installation, changed files during execution, or a hostile administrator.
No new endpoint, origin tag, certificate trust claim or independent accuracy
claim is introduced. Human and owner gates remain open while other work proceeds.
