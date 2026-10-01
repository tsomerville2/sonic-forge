"""sonic-forge — bytebeat music DSL + multi-engine TTS voice system."""

try:
    from importlib.metadata import PackageNotFoundError, version as _dist_version

    __version__ = _dist_version("sonic-forge")
except PackageNotFoundError:  # running from a source checkout that was never installed
    __version__ = "0+source"
