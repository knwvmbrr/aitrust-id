# FA preview discovery regression

Current64-command integration found a real stale assertion at SEO check43:
FA was still grouped with tags having no available checker. Its newly delivered
image helper is a planned tag with an optional container-details preview.

Change only the regression contract: retain no-checker assertions for every
unchanged tag and add FA-specific checks for Coming Soon, working=false, the
local image-details preview and absence of AI-origin/certification claims.
No production code or search copy changes; image observations remain distinct
from an independently validated FA tag. Execute the focused SEO tests, obtain
separate source review, then require current whole website evidence. Earlier
failed runs and unknown catalogue/mobile/prepare causes remain preserved.

The first focused assertion incorrectly read `working` on the catalogue rather
than its presentation view. Its failure was inspected and the test now uses
the existing `presentation(item).working` contract; no catalogue field was
invented and no production behavior was changed.
