NZ Harold
**********
A Dash app to fetch ad-free news from the NZ Herald.

Authors
=======
- Alexander Raichev (maintainer), 2025-07-04
- Jesse Prendergast, 2022-04


How to start work on this project
==================================
1. Using UV to manage this project, install the app dependencies via ``uv sync``.
2. Now let Fabric do the rest of the local initialisation via ``uv run fab init-local-env``.
   This entails initialising Git and Git Flow, activating the pre-commit hooks, creating a ``.env`` file, setting the proper Gunicorn port, and initialising the user database and adding a user 'test' with password 'test'.
3. Design, code, and test you app, possibly prototyping in a Marimo notebook in the ``notebooks`` folder.
4. Create your first release.
5. When you're ready to deploy the app to the web server, login to the Linode dashboard and create the domain nzherald.mrcagney.works.
   If you prefer a different domain name, that's fine, but then update the ``DOMAIN`` constant in ``fabfile.py`` to that different name.
   Finally, run ``uv run fab deploy-app``.
6. If your app has folders that Apache needs to write to, then additionally run ``uv run fab set-apache-permissions --dirname <folder name>`` for each such folder.
7. If you want to delete the app from the server (but not locally), because e.g. you messed up deployment and want to start afresh, then run ``uv run fab delete-app``.
8. If you create a new release later and want to update the app on the server, then run ``uv run fab update-app``.

Changelog
=========

1.0.0, 2025-07-03
-----------------
- First release base on prior work.
