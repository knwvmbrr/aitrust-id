# Offline image-score research reference

This optional development CLI is a learned reference computation, not an AI-origin detector release or an FA/PA tag. It uses a separately versioned adaptation of UniversalFakeDetect's unnormalized CLIP features plus linear head. A raw logit is not a probability or a verdict. A high score must not accuse a person; a low score does not establish human authorship.

**Current status:** implementation and synthetic/stdlib boundary controls exist. Exact native model execution has NOT been qualified yet. No weights or SDK were acquired locally. A missing-model invocation has actually returned Unavailable, and canonical PS remained usable. Hosted qualification below is proposed, not an executed result. Do not present this CLI as working model inference until its exact native qualification record is available.

## Declared profile

Initial target: Linux x86_64, Python3.13, CPU-only PyTorch 2.15.0+cpu, safetensors 0.8.0 and Pillow 13.0.0. Batch one and one CPU thread; no GPU, tokenizer, text model, dataset walk, training or implicit cache/download. The optional worker requires actual nonroot/no-new-privileges/zero capability sets and only loopback interfaces/routes. An ordinary connected host refuses before SDK import. No argument can assert away that check. A separately approved disposable runner establishes the isolated namespace and verifies its outer/inner identity.

Input is one canonical, non-symlink regular PNG/JPEG path, at most 10MiB and 4 million pixels. Supported PNG is noninterlaced8-bit RGB; alpha/grayscale/palette/animation remain Unsupported. JPEG uses the existing baseline single-scan8-bit three-component subset, then a real decoder must succeed. Valid unimplemented formats are Unsupported, not corrupt or AI-generated. The method uses stored RGB samples without EXIF orientation or ICC/gamma transformations; those differences matter when comparing with what a viewer displays.

Preprocessing follows the selected evaluator's center-crop-only semantics: no resizing, a 224-square crop, half-even rounding and black zero-padding for smaller axes, followed by fixed CLIP scaling/mean/std. It does not normalize the image-feature vector before the learned head. Very narrow images are cropped analytically into a fixed 224-square canvas, avoiding a potentially enormous intermediate padded image. Center crops can miss local edits and contextual evidence.

## Exact offline assets

Supply a trusted model directory containing only the selected publisher files needed by the loader:

- `model.safetensors`: OpenAI publisher HF revision `32bd64288804d66eefd0ccbe215aa642df71cc41`,1710540580 bytes, SHA256 `a2bf730a0c7debf160f7a6b50b3aaf3703e7e88ac73de7a314903141db026dcb`.
- `fc_weights.pth`: UniversalFakeDetect commit `030495aea3300a8b54c0ec37ec7fe1dd7e63c619`,4083 bytes, Git blob SHA1 `2a8efc8e238bf5a491e4fd5999655ed5eb3bbb72`. Its actual SHA256/layout are pending acquisition/qualification, not fabricated.

Despite the `.pth` suffix, the public worker never calls pickle, torch.load or TorchScript/JIT. It authenticates the exact small publisher blob first, then accepts only a closed tiny ZIP storage layout, CRC-checking but never evaluating `data.pkl`. Exactly768 finite F32 weights and one bias become deterministic safe-tensor data. An unexpected layout refuses. The large backbone is a publisher safetensors file, not an arbitrary selected checkpoint. Every byte is checked before native mapping and again afterward. No model file is fetched or selected from image metadata.

The adapted HF vision-state mapping and fixed OpenAI visual-source projection have their own method ID. No equivalence to the original TorchScript checkpoint or published benchmark is claimed without actual comparison. The code and model cards/rights facts are retained under `integrations/visual-score-reference/1.0.0/`. MIT notices are retained separately for Wisconsin AI and Vision Lab and OpenAI. The CLIP card's research/suitability warnings remain material. The original licensed OpenAI CLIP card stays unchanged. The separate Hugging Face README is linked by an authored factual reference (fixed URL/revision/blob/hash), without rehosting its modified prose or example or establishing its documentation-copy grant. This provenance-only correction does not change the numerical method or qualify model operation. No training/evaluation photograph rights, blanket legal clearance or distribution admission are inferred.

## Usage after qualification

Run only in an approved isolated, credential-free environment with the exact optional packages/assets already available. Do not install or download them on this Mac as part of these commands:

```sh
python3 -I -B scripts/inspect-visual-score.py /canonical/private/image.png \
  --model-dir /canonical/private/exact-models
```

Default output contains a raw reference logit and limits, or a fixed Unavailable reason/exit2. It does not print filenames, raw metadata, hashes or embeddings. It does not save a report/history. To explicitly export identities:

```sh
python3 -I -B scripts/inspect-visual-score.py /canonical/private/image.png \
  --model-dir /canonical/private/exact-models --json
```

JSON includes encoded-image/crop/model/source/runtime fingerprints that can link copies of the input. Review before saving or sharing it. It includes no raw image, embedding, creator name or metadata values. The input file stays untouched. Cancellation/deadline aborts/reaps the owned process; no secure memory erasure or parent/host-crash guarantee is claimed.

No observation is an origin assertion, authentication, authorship judgment, truth finding or a general localized-manipulation detector. No numeric threshold or FA/PA issuance is implemented. T-FA/T-PA full acceptance and human/independent evidence remain open. F-019 is unrelated MT scope.

Focused stdlib controls:

```sh
python3 -I -S -B -m unittest discover -s tests -p test_visual_score.py -v
```

These controls use synthetic bytes and inert mapping objects plus actual stdlib subprocesses. They do not run a learned model or measure accuracy. The separately proposed [hosted qualification](offline-image-score-qualification-plan.md) must be reviewed and executed before a functioning native-model claim.

The crop semantics are pinned to the retained Torchvisionv0.14.1 reference. The selected UFD requirements.txt URL returned404; its actual package version is not known from that query. Matching a source-level crop rule is not native upstream parity. A read-only nonregular FIFO is refused before it can block. Invalid CLI arguments return a fixed message rather than echoing arbitrary values.

Implementation hashes in explicit JSON describe current checkout files, checked before/after the method and by its parent consumer. They do not independently attest execution, replay the learned inference or establish model accuracy.

The parent owns the private read-only temporary HOME before spawning the worker. The child only uses its identity-checked directory handle; after ordinary deadline/cancellation and reap, the parent removes its own empty directory. A replacement or unexpected private content is retained and reported as cleanup_uncertain, with no accepted score. No recursive stage deletion is used.
