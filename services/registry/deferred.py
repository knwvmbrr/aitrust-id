"""Refuse the deferred registry before imports, network or storage can activate."""
MESSAGE = 'AI Trust ID registry is deferred from this release. No registry storage or listener was started.'
EXIT_DEFERRED = 64

def main():
    print(MESSAGE)
    return EXIT_DEFERRED

if __name__ == '__main__':
    raise SystemExit(main())
