# V05/V06: first camera cohort and detector research candidate

Source-only candidate research, captured 2026-11-22 and made durable on an isolated development branch. No image, model weight, dataset, package or binary was acquired; no detector was installed or executed. This is not FA/PA issuance, an accuracy result, production integration or an original requirement closure. [Source-only research receipt](../runs/2026-11-22-visual-camera-detector-source-research.json).

## V05: camera-source cohort

Use a **per-file CC0-only selection from [raw.pixls.us](https://raw.pixls.us/)**. Its submission form asks contributors to declare ownership, dedicate the file to CC0, and supply an unmodified copy from card/camera. It requests scenery rather than people. These are positive contributor declarations, not independently established camera-origin truth.

The catalogue mixes older licensing records and converted files. The publisher explicitly identifies [legacy non-CC0 samples](https://pixls.us/blog/2017/09/keep-the-raws-coming/). Exclude those, Adobe DNG Converter rows, and rows whose provenance remarks conflict with the intended camera-original cohort. Never treat the entire site as one CC0 dataset.

A concrete first candidate is catalogue ID **915**, Apple iPhone 6s Plus, 16-bit DNG, 12.19 megapixels, displayed size 9.75 MB, date 2017-01-17. The row links CC0 and publishes digest `845fee4f09c832af3728778737f5ae9b99124debb821b6e2066b94aed1daa91c`. The asset was not fetched, so that digest and the approximate size are publisher assertions, not locally verified bytes. Its URL is [the catalogue's exact download link](https://raw.pixls.us/getfile.php/915/nice/Apple%20-%20iPhone%206s%20Plus%20-%2016bit%20(4:3).DNG).

[CC0's official deed](https://creativecommons.org/publicdomain/zero/1.0/) expressly permits commercial copying, modification and redistribution. It does not clear privacy/publicity, patent or trademark rights or warrant the contributor's ownership. Preserve per-item source and dedication evidence and screen selected scenes before redistribution. A CC0 dedication does not authenticate origin.

The 12.19 MP DNG exceeds the current 4 MP JPEG tool limit and cannot go directly into the JPEG/PNG-only tools. A separately versioned engineering preparation job needs a separately reviewed RAW decoder and exact recorded conversion, with output bounded to the existing image subset. Preserve the original privately; tie every JPEG/PNG/crop/recompression to the same source family. A derived image is labelled as a transformation of a declared camera sample, not as independently proved camera output. Do not split derivatives or same scene/camera/contributor across calibration and held-out evaluation.

## V06: UniversalFakeDetect candidate

Use the publisher's [UniversalFakeDetect repository](https://github.com/WisconsinAIVision/UniversalFakeDetect/tree/030495aea3300a8b54c0ec37ec7fe1dd7e63c619), pinned to **030495aea3300a8b54c0ec37ec7fe1dd7e63c619**. Its selected path is CLIP ViT-L/14 image features followed by a learned **768-to-1 linear head**. This is an image-generation detector candidate, not a VLM description model and not a localized manipulation detector.

License/identity chain:

- The [pinned repository license](https://raw.githubusercontent.com/WisconsinAIVision/UniversalFakeDetect/030495aea3300a8b54c0ec37ec7fe1dd7e63c619/LICENSE) is MIT, copyright Wisconsin AI and Vision Lab. Retain that notice for code and the repository-delivered head; no separate head license appears in the complete published tree.
- The official [tree metadata](https://api.github.com/repos/WisconsinAIVision/UniversalFakeDetect/git/trees/030495aea3300a8b54c0ec37ec7fe1dd7e63c619?recursive=1) identifies `pretrained_weights/fc_weights.pth` as 4,083 bytes, Git blob `2a8efc8e238bf5a491e4fd5999655ed5eb3bbb72`. This is metadata only; its SHA-256 and tensor contents remain unverified until an engineering-qualified acquisition. Git blob SHA-1 is not a claimed SHA-256.
- The vendored [CLIP loader](https://raw.githubusercontent.com/WisconsinAIVision/UniversalFakeDetect/030495aea3300a8b54c0ec37ec7fe1dd7e63c619/models/clip/clip.py) selects the official ViT-L/14 checkpoint with published expected SHA-256 `b8cca3fd41ae0c99ba7e8951adf17d267cdb84cd88be6f7c2e0eca1737a03836`. No checkpoint was retrieved. OpenAI's [CLIP license](https://raw.githubusercontent.com/openai/CLIP/main/LICENSE) is MIT; retain its distinct notice rather than relabelling vendored code as solely the detector author's work. The observed upstream CLIP head is `d05afc436d78f1c48dc0dbf8e5980a9d471f35f6`; pin relevant source/license files there before implementation.
- Framework/decoder dependencies need their own pinned package/native notice inventory. Neither repository MIT license grants rights to their training or evaluation photographs. The detector README points to an external ProGAN/ForenSynth training corpus; do not bundle or train on it under an assumed code license. CLIP's image-caption training corpus is not released. No training-data redistribution permission is inferred.

The [CLIP model card](https://raw.githubusercontent.com/openai/CLIP/main/model-card.md) describes research use and treats deployment as out of scope without task-specific study. That guidance is distinct from the MIT copyright grant and remains a material suitability limit. This recommendation is for offline qualification, not product admission.

### Runtime and serialization hazards established in actual source

The [published evaluator](https://raw.githubusercontent.com/WisconsinAIVision/UniversalFakeDetect/main/validate.py) calls `.cuda()` on model/input, defaults to batch 128 with four loader workers, loads its head through unrestricted `torch.load`, accepts pickle dataset lists, deletes an existing result directory, and optimizes a threshold against supplied evaluation labels. The backbone loader downloads implicitly into HOME's cache. Do not execute this evaluator against product inputs unchanged.

No minimum VRAM, CPU RAM, runtime latency, or exact checkpoint byte size was established here. The unmodified evaluator requires CUDA; the model constructor initially loads CLIP on CPU. An isolated CPU adapter is plausible from source, but has not been tested. A large backbone plus framework is inappropriate for this Mac's present reserve. No speed, phone/browser, or GPU-free functioning claim is made.

The output is a learned logit/sigmoid score. It is not a calibrated probability of AI origin, authentication, authorship, deception or whole-image manipulation. Centre-cropped 224-pixel observations can miss local edits and be affected by compression, resizing, screenshots, rendering and unseen generator/camera families. A high score must never accuse a person; a low score must never mean human-made.

## One concrete next implementation job, after engineering rights, measured capacity and worker-plan checks

Routine, already authorized free engineering work does not require another owner approval. The implementer verifies source and reuse rights, actual disk/memory capacity and a bounded worker plan before acquisition. Model acquisition remains pending those checks; no installation runs locally below the existing reserve. Owner decisions are reserved for new costs, credentials, terms acceptance, legal representation or adoption of a numeric tag policy. This note grants none of those.

Build an **offline single-image score qualification adapter**, not a tag issuer. Proposed owned files: `tools/visual_detector_observation.py`, `scripts/inspect-visual-score.py`, `tests/test_visual_detector_observation.py`, a finite source/weight/notice manifest, and a qualification-only workflow. Do not install or fetch from an input file or request.

1. Pin the exact source/license chain above. Acquire only the selected head and backbone in an owned disposable environment after measured capacity and rights checks, verify their exact digests before loading, and retain actual sizes and installed dependency identities. Never execute `.pyc` files shipped in the upstream tree.
2. Require a non-executable tensor checkpoint format. If a publisher conversion is unavailable, a one-time **trusted digest-pinned**, network-disabled conversion may use a reviewed `weights_only=True` state-dict reader with closed tensor keys/shapes/dtypes/finiteness and byte limits; emit fixed safetensors and bind both digests. No arbitrary pickle/JIT loader in the public input path. Unsupported serialization refuses.
3. Use a credential-free network-disabled owned worker with batch one, fixed transforms, bounded input file/pixels/output and parent-owned wall/CPU/memory limits plus kill/reap. No implicit download, HOME mutation, recursive dataset walk, private path logging or input-selected code. Size/model memory qualification must precede any runtime promise.
4. Exercise actual load/use/remove, missing/corrupt weights, oversized/malformed image, deadline/cancel/reap, no-egress and recovery plus PS independence. Compare full raw observations to the pinned reference on fixed engineering cases. Preserve failed attempts. No benchmark or release gate is passed by this exercise.
5. Separately prepare the CC0 camera-family manifest and rights-reviewed generated-family cohort. Freeze source-family splits before any calibration; keep generator/version/prompt/scene derivatives together and hold out camera models/contributors/scenes. Report false positives per camera/transform group, coverage and uncertainty; no threshold selection from the held-out set. Independent acceptance and any tag decision remain separate.

An exact source-only tree query already usable without weights is the linked official GitHub tree endpoint. The next executable *runtime* step is the bounded adapter above after these engineering checks and implementation; there is no fabricated ready CLI or claimed runtime here.

### One rejected tempting alternative

[Tiny-LaDeDa's official pinned license](https://raw.githubusercontent.com/barcavia/RealTime-DeepfakeDetection-in-the-RealWorld/e734562bbb6763f5bb2951099e9dc9a38df5e7dd/LICENSE) limits grants to research and requires a separate Yissum commercial license for commercial use/distribution. Its small architecture does not remove that restriction, so it is not selected for a product-compatible deployment route. No broader model search is needed for this bounded recommendation.
