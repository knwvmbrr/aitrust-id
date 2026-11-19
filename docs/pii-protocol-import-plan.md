# Traversable shared ASGI modules

The hosted startup diagnostic reports process exit 1, three restarts, no OOM
kill and no completed health probes. Uvicorn repeatedly reports that it cannot
import `protocol.http_privacy`. Its pinned 0.34.0 importer emits that message
when the named module cannot be found. Import failures in dependencies have
their own exception paths.

Each selected image creates the protocol directory with a multi-file
`COPY --chmod=0444`. BuildKit can apply the supplied mode to newly created
destination directories. A Python package directory needs search permission
to load its files. The repository uses an intentional namespace package, and
adding an empty initializer would leave a non-traversable directory unreadable.

The local nonroot import control reproduces the exact Uvicorn message with
directory mode 0444. Mode 0555 permits loading the same factory and retains
the original module bytes and file mode 0444. The hosted receipt does not
include filesystem modes, so its exact directory mode remains unobserved.

After each protocol copy, print only that directory’s mode to the build log,
then explicitly set the directory to 0555. After
`USER 10001:10001`, add a build-time module-resolution assertion for the exact
`/app/protocol/http_privacy.py` path. This check does not load the service or
ML model. A package collision, missing source or traversal failure stops the
image build before startup.

Run a fixture-built filesystem through the real pinned Uvicorn CLI’s config
loader without starting a server. Check the failure and corrected cases,
source/file mode preservation, image commands and nonroot build assertion.
The actual hosted build and healthy service/replay checks must still pass.
Existing resource, network, user and read-only runtime controls remain required.

The BuildKit maintainers describe created-parent mode handling in
[issue 6801](https://github.com/moby/buildkit/issues/6801). The explicit directory
mode avoids depending on the frontend’s implicit parent permission choice.
