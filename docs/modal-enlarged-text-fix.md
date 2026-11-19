# Keep enlarged-text modals readable

Visual QA of the real MT modal at 320px and 200% root text enlargement found
that rem-scaled padding and close-button width left a narrow title/result column.
The previous horizontal-scroll assertion passed despite fragmented words.

Keep text enlargement intact. On narrow viewports reduce only chrome spacing,
use a stable 44px close target, and give the modal body and MT result their usable
width back. Preserve the existing Radix focus/escape behavior, labels, theme and
worker/data boundaries. Do not shrink text, disable zoom or migrate components.

Add actual built-modal checks for a bounded sticky-header height and an unbroken
result word, alongside existing reflow, request binding, privacy and failure
containment. Inspect the new screenshot; automated checks are not human VoiceOver
or physical iPhone acceptance.
