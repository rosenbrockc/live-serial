# Unit Tests for Live Serial

Because of the interconnectedness of the modules in this package, we don't have
the unit tests split up by module. Instead, the main script
`liveserial/livemon.py` is tested repeatedly with different combinations of
command-line arguments to simulate user-choices.