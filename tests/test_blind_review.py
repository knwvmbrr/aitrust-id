import csv
import json
import stat
import pytest
from test_release_policy import module

review = module('scripts/prepare-ps-review.py')


def packet(tmp_path):
    source = tmp_path/'new.jsonl'
    source.write_text(json.dumps({'id':'one','text':'=Synthetic spreadsheet string',
                                 'category':'display','source':'authored synthetic'})+'\n')
    destination = tmp_path/'packet'
    manifest = review.freeze(source, destination)
    return source, destination, manifest


def test_blind_packet_has_no_prediction_or_label_and_private_modes(tmp_path):
    _, path, manifest = packet(tmp_path)
    assert not manifest['independence_verified'] and not manifest['predictions_run']
    assert stat.S_IMODE(path.stat().st_mode) == 0o700
    for file in path.iterdir():
        assert stat.S_IMODE(file.stat().st_mode) == 0o600
    with (path/'reviewer-1.csv').open() as handle:
        row = next(csv.DictReader(handle))
        assert row['label'] == '' and row['text'].startswith("'=")
    with pytest.raises(FileExistsError):
        review.freeze(tmp_path/'new.jsonl', path)


def test_incomplete_review_and_changed_dataset_fail(tmp_path):
    _, path, _ = packet(tmp_path)
    with pytest.raises(ValueError, match='Every item'):
        review.compare(path)
    (path/'items.jsonl').write_text('{}\n')
    with pytest.raises(ValueError, match='changed'):
        review.compare(path)


def test_disagreement_remains_visible_and_is_not_release_evidence(tmp_path):
    _, path, _ = packet(tmp_path)
    for i,label in [(1,'positive'),(2,'ambiguous')]:
        file=path/f'reviewer-{i}.csv'
        with file.open() as handle: rows=list(csv.DictReader(handle))
        rows[0].update(label=label,reason='Synthetic test review only')
        with file.open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=review.FIELDS);writer.writeheader();writer.writerows(rows)
    result=review.compare(path)
    assert result['disagreement_ids'] == ['one'] and result['ambiguous_ids'] == ['one']
    assert result['release_assessed'] is False and result['independence_verified'] is False


def test_preexisting_labels_cannot_be_recycled_as_blind_input(tmp_path):
    source=tmp_path/'bad.jsonl'
    source.write_text(json.dumps({'id':'one','text':'sample','category':'display','source':'test','labels':['PS']})+'\n')
    with pytest.raises(ValueError, match='no labels'):
        review.freeze(source,tmp_path/'packet')
