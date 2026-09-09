# Maintenance source only

`_remove_old_utils.py` is preserved byte-for-byte from the upstream source for
source completeness. It is not imported by the MCP service, not an installer
step, and not a health check. Executing it attaches to an active Aspen document,
removes named utilities, reinitializes and runs that model. Do not run it during
installation, testing, protocol discovery, or ordinary backend startup.

Its presence does not authorize changes to any existing model. The offline
runtime and protocol tests never execute this file.
