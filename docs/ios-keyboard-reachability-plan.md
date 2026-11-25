# Native keyboard reachability

Approved before implementation on 2026-11-25. Scope: N-013, F-035 and F-094.
Source starts at `fb35498ea18e2dbaed783428a4d08b1e57b4d89e`; its runtime
sources match the separately qualified `c721186a` cohort.

The genuine seven-flow run passed. The subsequent layout matrix passed all
three small-phone configurations, then failed on regular/light-standard before
checking or clearing anything. The keyboard covered the Check button. Eight
unchanged drag attempts began inside the focused editor and did not move the
outer content. Nested-editor gesture interception is an inference; no responder
trace was captured. Both owned guests were removed. The failed attempt remains
in `runs/2026-11-25-ios-current-layout-matrix.json`.

Give people an explicit **Done editing** keyboard action that keeps their text.
Also dismiss the keyboard when a drag begins in either the editor or containing
scroll view. Keep editor scrolling enabled and allow short text to begin a
vertical drag. App and Share use the same controller and behavior.

Use UIKit's standard Done toolbar item with an accessible label and existing
brand colors. Done only resigns first responder: it never runs a check, clears
text, cancels Share, changes a result or sends data. Existing checking, Clear,
generation cancellation and background privacy behavior stay intact.

The installed Xcode 27.2 UIKit declarations establish the selected mechanisms:
`UIScrollView.keyboardDismissMode = .onDrag` dismisses when a drag starts;
`alwaysBounceVertical` with `bounces` permits a short-content vertical drag;
`UITextView.inputAccessoryView` is writable. Standard Done supports target/action.
No SDK installation or new dependency is needed.

Keep the layout fixture byte-identical, including its original gesture geometry,
assertions, eight-attempt limit and all execution budgets. Keep all seven test
IDs and original assertions; add actual Done, keyboard dismissal, unchanged-text
and no-automatic-check checks within the existing App and Share cases. Update
only the matrix's literal seven-suite digest after those additions.

Freeze and independently review the changed source before any new native run.
The original full seven and complete four-profile/three-configuration matrix
must both run on the changed source; the old pass cannot be rebound. Keep
120-second case, 150-second maximum, 780-second UI and 1,800-second matrix-device
budgets, owned cleanup and full-size visual review. Stop on failure and diagnose
before retrying. Toolbar layout, short-text dragging and enlarged text need
actual verification. Physical iPhone, human VoiceOver, new Apple distribution
and full original requirements remain separate gates.
