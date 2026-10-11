# Compare two passages locally — research tool

Choose two passages from one English text and inspect what one pinned model says about their relationship. This is a working offline research command, separate from the PS and PII checkers. It does not issue HP or any other tag, establish truth or decide someone’s intent. The self-contradiction signal remains proposed. Its larger detector, automatic sentence selection, independent accuracy checks and tag integration remain open. The retrieved-passage signal F-020b is a separate job and is not implemented by this tool.

The first real tests found an error: the model called “The sky is blue.” and “There are five books on the shelf.” a contradiction. Both statements can be true. This case remains in the published execution evidence. Normalized scores describe the model’s output, not measured probabilities or independent corroboration.

## Set up once

The exercised environments are Apple Silicon macOS with Python 3.12 and x86-64 Debian Linux with Python 3.13 and system libseccomp2 2.6.0. Other versions and architectures are not accepted as tested. Linux needs no root permission for inference. Unsupported sandbox controls refuse to run. Use a separate research environment; do not install these packages into your working gateway, evaluator or redactor.

Create a private directory outside the checkout. In the commands below, replace `PRIVATE` with that directory and `REPO` with your checkout’s absolute path. Downloads are about 300 MB for the model assets, plus platform-specific packages. Setup uses the internet; inference does not.

```sh
install -d -m 700 PRIVATE
python3 -m venv PRIVATE/nli-env
```

On Apple Silicon Python 3.12:

```sh
PRIVATE/nli-env/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes -r REPO/research/nli/requirements-mac.lock
```

On x86-64 Linux Python 3.13:

```sh
PRIVATE/nli-env/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes -r REPO/research/nli/requirements-linux.lock
```

Download the pinned public assets into a new private directory:

```sh
python3 REPO/scripts/fetch-nli-assets.py --cache PRIVATE/nli-assets
```

This checks each downloaded file’s exact length and SHA-256 before saving anything. It never reads an example or executes a model. Existing cache directories are refused. Version-specific official PyPI wheel identities and preserved notice text are in `research/nli/`. These are retained declarations and notices, not a legal clearance or model security audit. The model card declares Apache-2.0 and training on SNLI/MultiNLI; its claims are not our product’s accuracy. The model and its upstream base/data obligations still need qualified review before a detector release.

## Run a comparison

Save this synthetic example as `PRIVATE/input.json`, then set its permissions to `600`:

```json
{"schema_version":1,"language":"en","text":"The door is closed. The door is open.","pairs":[{"id":"example","first":[0,19],"second":[20,37]}]}
```

Spans use original Unicode character offsets: the first number is included and the second is excluded. They must not overlap. The first passage is the model’s premise and the second its hypothesis; reversing them can change the answer. The tool never truncates text silently or guesses which passages you intended.

```sh
chmod 600 PRIVATE/input.json
PRIVATE/nli-env/bin/python REPO/scripts/check-nli-pairs.py PRIVATE/input.json --model-cache PRIVATE/nli-assets --details PRIVATE/result
```

The short console summary tells you whether evaluation succeeded and whether private details were saved. Open `PRIVATE/result/observations.json` to see each pair’s labels, all three raw scores, original spans, subject hash and method identities. The details omit the text, but hashes and spans may still reveal or link information. Keep them private. No result or example is uploaded, enrolled in research or included in training. Sharing is your separate decision. Existing result directories are never overwritten.

An input or method failure returns exit status 2, a fixed diagnostic and no usable result. The whole job refuses if any selected pair fails. Limits: 20,000 source characters, 16 pairs, 2,000 characters per passage, 512 model tokens per pair, 262,144 input bytes, 35 CPU seconds and 45 wall seconds for the worker. Linux adds a 2 GiB address-space limit; macOS has the tested CPU/wall bounds without an address-space guarantee.

## Check it and remove it

```sh
python3 REPO/scripts/verify-nli-profile.py
PRIVATE/nli-env/bin/python REPO/scripts/verify-nli-pairs.py --python PRIVATE/nli-env/bin/python --model-cache PRIVATE/nli-assets --output output/verification/nli-controls.json
```

The second command runs only invented local examples and records engineering controls. Its output destination must be repository-relative under `runs/` or `output/`; it is not independent accuracy evidence. Default CI tests the contracts and Linux sandbox without downloading weights. Full installed-model execution evidence is recorded separately.

To remove the tool’s local data, delete the private environment, asset cache, inputs and results you created. No background service or system configuration is installed. Stop using this model if it cannot separate genuine contradictions from compatible or unrelated statements; retain failed examples rather than retuning an independent holdout.

## Trust boundary

Pinned file identities are checked before graph interpretation. The loader refuses custom operators, graph functions, external tensors, unknown labels, overlong token sequences and malformed scores. CPU inference uses one thread per execution pool. A dedicated child process receives only the bounded input and a cleared environment. macOS launches it under an OS deny-network profile and checks an actual denied connection before loading the model. Linux requires no-new-privileges, thread synchronization and network/io_uring syscall denial, tested with real sockets and a descendant process. Ordinary personal routes retain their own dependencies and permissions.

This does not defend against a compromised administrator, a malicious process running as your account, malicious trusted native libraries, or a modified Python/runtime/checkout. The Mac sandbox mechanism may become unavailable on a future OS; that is a refusal condition, not permission to run unprotected. This is one model and one perspective, not multiple independent sources.

Sources: [pinned upstream model card](https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall/tree/a150876415327c80daeff35ca6f68f5ed8cf5c24), [ONNX Runtime](https://onnxruntime.ai/docs/), [libseccomp API](https://github.com/seccomp/libseccomp/tree/v2.6.0).
