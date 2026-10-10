"""Shared accessibility release gate; automated checks cannot replace people."""
from datetime import datetime,timezone
from pathlib import Path
import re
from protocol.revalidation import ROOT,assess,fingerprint

TECHNOLOGIES={'NVDA','VoiceOver'}
SURFACES={'website','extension'}
TASKS={'navigate','read_tag','open_details','close_restore_focus','errors_and_status','zoom_reflow'}

def assess_reviews(reviews,receipts,root=ROOT):
    failures=[];accepted=set()
    for surface in SURFACES:
        status=assess(receipts.get(surface,{}),surface,root)
        if not status['pass']:failures.append(surface+':automated_evidence_missing_or_stale')
    for review in reviews:
        try:
            surface=review['surface'];technology=review['technology']
            if surface not in SURFACES or technology not in TECHNOLOGIES:raise ValueError()
            pair=(surface,technology)
            if pair in accepted:raise ValueError()
            if review['kind']!='human_accessibility_review' or review['engineering_fixture'] is not False or review['human_performed'] is not True:
                raise ValueError()
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._-]{1,79}',review['reviewer_public_label']) or review['reviewer_publication_consent'] is not True:
                raise ValueError()
            if review['fingerprint']!=fingerprint(surface,root)['sha256']:raise ValueError()
            date=datetime.fromisoformat(review['performed_at'])
            if date.tzinfo is None or date>datetime.now(timezone.utc):raise ValueError()
            if not isinstance(review['environment'],str) or not review['environment'].strip() or len(review['environment'])>300:raise ValueError()
            if set(review['tasks'])!=TASKS or any(v!='pass' for v in review['tasks'].values()) or review['unresolved_issues']!=[]:
                raise ValueError()
            # Evidence is a separately recorded, reviewer-approved account, not
            # a screenshot of private content or an AI-generated test transcript.
            evidence=review['account']
            if not isinstance(evidence,str) or not evidence.startswith('docs/manual-accessibility/') or '..' in Path(evidence).parts:
                raise ValueError()
            file=root/evidence
            if file.is_symlink() or any(parent.is_symlink() for parent in file.parents if parent!=root and root in parent.parents) or not file.is_file() or file.stat().st_size>100_000 or len(file.read_text().strip())<80:
                raise ValueError()
            accepted.add(pair)
        except (KeyError,ValueError,TypeError,OSError):failures.append('manual_review_invalid_or_stale')
    missing={(s,t) for s in SURFACES for t in TECHNOLOGIES}-accepted
    failures.extend(s+':'+t+':human_review_required' for s,t in sorted(missing))
    return {'pass':not failures,'failures':failures,'accepted_human_reviews':len(accepted),
            'full_wcag_conformance':False,'independent_tag_accuracy':False,
            'manual_reports_are_reviewer_attestations_not_identity_proof':True}
