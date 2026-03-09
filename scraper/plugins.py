"""
Plugin loader — discovers third-party transforms and storage backends via
importlib.metadata entry_points.

Plugin packages register extensions in their pyproject.toml:

  [project.entry-points."scrapit.transforms"]
  my_transform = "my_pkg.transforms:my_fn"

  [project.entry-points."scrapit.storage"]
  redis = "my_pkg.storage:RedisBackend"

Call load_plugins() once at startup to register everything.
"""

from importlib.metadata import entry_points


def load_plugins():
    """Discover and register all scrapit plugins."""
    _load_transforms()
    _load_storage()


def _load_transforms():
    try:
        eps = entry_points(group="scrapit.transforms")
    except TypeError:
        eps = entry_points().get("scrapit.transforms", [])

    from scraper.transforms import _registry
    for ep in eps:
        try:
            fn = ep.load()
            _registry[ep.name] = fn
        except Exception as e:
            from scraper.logger import log
            log(f"plugin: failed to load transform '{ep.name}': {e}", "warning")


def _load_storage():
    try:
        eps = entry_points(group="scrapit.storage")
    except TypeError:
        eps = entry_points().get("scrapit.storage", [])

    for ep in eps:
        try:
            ep.load()  # registers side-effects on import
        except Exception as e:
            from scraper.logger import log
            log(f"plugin: failed to load storage '{ep.name}': {e}", "warning")
