"""briefbench: rewrite rough prompts into briefs, and log every rewrite."""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("briefbench")
except PackageNotFoundError:  # a source tree that is not installed
    __version__ = "0+unknown"
