======================
Python Tomorrow.io API
======================


.. image:: https://img.shields.io/pypi/v/pytomorrowio.svg
        :target: https://pypi.python.org/pypi/pytomorrowio

.. image:: https://img.shields.io/travis/raman325/pytomorrowio.svg
        :target: https://travis-ci.com/raman325/pytomorrowio

.. image:: https://readthedocs.org/projects/pytomorrowio/badge/?version=latest
        :target: https://pytomorrowio.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status



Python3.7+ package to access the `Tomorrow.io Weather API <https://www.tomorrow.io/weather-api/>`_

Both an async module (``TomorrowioV4``) and a synchronous module
(``TomorrowioV4Sync``) are provided.

Example Code
-------------
.. code-block:: python

  from pytomorrowio import TomorrowioSync
  api = TomorrowioV4Sync("MY_API_KEY", latitude, longitude)
  print(api.realtime(api.available_fields(timedelta(0))))
  print(api.forecast_nowcast(api.available_fields(timedelta(minutes=5))), start_time, timedelta_duration, timestep))

Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
