# Directory clock-skew fencing repair

The provider contract admits token issue times up to five seconds ahead of the
broker clock. A local recovery fence at the broker's current second therefore
cannot cover every already-issued token that the same provider contract accepts.
The same defect can revalidate a logged-out token when the bounded logout journal
rolls over. A synthetic provider-contract and journal reproduction demonstrated
an older token issued three seconds ahead surviving recovery.

Keep the accepted five-second clock tolerance, role model, tenant boundaries and
personal independence. Put both recovery and logout-rollover fences beyond the
entire accepted issue-time interval, preserve a monotonically increasing fence,
and require a fresh login after that fence. Document the short wait; do not call
a numeric token timestamp a measured probability or an identity assurance.

Test both ends of the accepted future interval and the 10,000-entry logout
rollover. Re-run the real Keycloak/PostgreSQL workflow with the documented wait,
then rebind current evidence, scope, changelog and public guide. No hosted login,
new endpoint, new tag, collection, additional provider permission or global
security certification is introduced. Provider and broker clocks must be kept
synchronized within the declared tolerance.
