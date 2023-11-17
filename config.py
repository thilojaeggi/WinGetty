
from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="WINGETTY",
    settings_files=['settings.toml', '.secrets.toml'],
    VERSION = "0.0.9",
    PREFERRED_URL_SCHEME = "https"
)

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
