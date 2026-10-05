from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("clef-use")
except PackageNotFoundError:
    __version__ = "0.1.19"
