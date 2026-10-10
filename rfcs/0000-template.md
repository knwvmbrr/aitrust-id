# RFC 0000: <title>

- **Author:**
- **Date:**
- **Status:** draft | comment | accepted | rejected
- **Affects:** taxonomy | signals | spec | governance

## Summary

One paragraph. What changes and why.

## Motivation

What goes wrong today. Give a concrete example of an output that is mislabeled or unlabeled
under the current taxonomy.

## Detection basis

**Required for any taxonomy change.** How is this detected? Be specific enough that someone
else could implement it from this section alone.

## Dataset

**Required.** Where are the labeled fixtures? How many? How were they labeled, by how many
annotators, and what is the measured inter-annotator agreement (Krippendorff's alpha)?

> State agreement and uncertainty separately from precision, recall and calibration.
> An agreement coefficient is not a model-confidence ceiling. Fix the claim-specific
> sampling, annotation and metric method before evaluation; do not choose gates after
> seeing the result.

## Measured performance

Precision, recall, and ECE on a held-out split. Include the confusion matrix.

## Failure modes

Where does this signal produce false positives? What benign content looks like a hit?

## Accessibility impact

How does this label announce to a screen reader? What is its full aria-label sentence?

## Alternatives considered

## Open questions
