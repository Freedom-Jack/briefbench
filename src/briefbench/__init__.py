"""briefbench: blind paired trials of prompt treatments, such as the brief skill, on your own tasks."""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("briefbench")
except PackageNotFoundError:  # a source tree that is not installed
    __version__ = "0+unknown"
