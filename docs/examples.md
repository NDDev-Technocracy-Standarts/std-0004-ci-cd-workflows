# Executable routing example

The same admission operation is runnable without GitHub or private authoring tools.

    >>> from nddev_cicd.routing import select
    >>> select("public", "linux")["runner"]
    ['ubuntu-24.04']
    >>> select("private", "linux", trusted=True, private_labels=["self-hosted", "Linux", "fixture-linux"])["provider"]
    'self-hosted'
