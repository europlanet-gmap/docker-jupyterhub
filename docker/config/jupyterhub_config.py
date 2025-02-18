# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os
import sys
import importlib.util

# ================================
# Utility: Import local modules
# ================================

_THISDIR = os.path.dirname(__file__)


def _import_module(module_name):
    """
    Import a module from a .py file in the current directory.
    """
    filepath = os.path.join(_THISDIR, f"{module_name}.py")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Module file '{filepath}' not found")
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import local modules
utils = _import_module("utils")
custom_spawner = _import_module("custom_spawner")


# ================================
# JupyterHub & DockerSpawner Setup
# ================================

c = get_config()

# Use the custom Docker spawner
c.JupyterHub.spawner_class = custom_spawner.CustomDockerSpawner

# Configure allowed Docker images (read from file)
_images = utils.read_txt('imagelist')
c.DockerSpawner.allowed_images = _images

# Set DockerSpawner command and network settings
c.DockerSpawner.cmd = os.environ["NOTEBOOK_SPAWN_CMD"]
c.DockerSpawner.network_name = os.environ["DOCKER_NETWORK_NAME"]
c.DockerSpawner.use_internal_ip = True

# Notebook directory (default: /home/jovyan)
notebook_dir = os.environ.get("NOTEBOOK_DIR", "/home/jovyan")
c.DockerSpawner.notebook_dir = notebook_dir

# -------------------------------
# Volume Mapping Settings
# -------------------------------

# User's work directory (with {username} placeholder)
docker_work_dir = os.environ["NOTEBOOK_USERS_WORK_DIR"]
local_work_basedir = os.environ["HOST_USERS_WORK_BASEDIR"]
local_work_dir = f"{local_work_basedir}/{{username}}"

# Shared and data directories
docker_shared_dir = os.environ["NOTEBOOK_USERS_SHARED_DIR"]
local_shared_dir = os.environ["HOST_USERS_SHARED_DIR"]

docker_data_dir = os.environ["NOTEBOOK_DATA_DIR"]
local_data_dir = os.environ["HOST_DATA_DIR"]

docker_isisdata_dir = os.environ["NOTEBOOK_ISISDATA_DIR"]
local_isisdata_dir = os.environ["HOST_ISISDATA_DIR"]

c.DockerSpawner.volumes = {
    local_work_dir: docker_work_dir,
    local_data_dir: docker_data_dir,
    local_shared_dir: docker_shared_dir,
    local_isisdata_dir: docker_isisdata_dir,
}

# Ensure extra_create_kwargs exists and update with user root
if not hasattr(c.DockerSpawner, "extra_create_kwargs") or c.DockerSpawner.extra_create_kwargs is None:
    c.DockerSpawner.extra_create_kwargs = {}
c.DockerSpawner.extra_create_kwargs.update({"user": "root"})

# Set environment variables for the spawned container
c.DockerSpawner.environment = {
    "CHOWN_HOME": "yes",
    "CHOWN_EXTRA": docker_work_dir,
    "CHOWN_HOME_OPTS": "-R",
    "NB_UID": 1000,
    "NB_GID": 100,
    "WORK_DIR": docker_work_dir,
    "DATA_DIR": docker_data_dir,
    "ISISDATA_DIR": docker_isisdata_dir,
}

# Remove containers when stopped and enable debugging
c.DockerSpawner.remove = True
c.DockerSpawner.debug = True

# Hub network and persistence settings
c.JupyterHub.hub_ip = "jupyterhub"
c.JupyterHub.hub_port = 8080
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"


# ================================
# Multi-Authenticator Configuration
# ================================

if "OAUTHENTICATOR" in os.environ:
    auth_type = os.environ["OAUTHENTICATOR"].upper()

    if auth_type == "AUTHENTIK":
        # Ensure all required Authentik variables are provided
        required_vars = [
            "OAUTH_CLIENT_ID",
            "OAUTH_CLIENT_SECRET",
            "OAUTH_CALLBACK_URL",
            "OAUTH_AUTHORIZE_URL",
            "OAUTH_TOKEN_URL",
            "OAUTH_USERDATA_URL",
        ]
        for var in required_vars:
            if not os.environ.get(var):
                raise EnvironmentError(f"{var} environment variable is required for Authentik")

        from oauthenticator.generic import GenericOAuthenticator

        c.JupyterHub.authenticator_class = GenericOAuthenticator
        c.GenericOAuthenticator.client_id = os.environ["OAUTH_CLIENT_ID"]
        c.GenericOAuthenticator.client_secret = os.environ["OAUTH_CLIENT_SECRET"]
        c.GenericOAuthenticator.oauth_callback_url = os.environ["OAUTH_CALLBACK_URL"]
        c.GenericOAuthenticator.authorize_url = os.environ["OAUTH_AUTHORIZE_URL"]
        c.GenericOAuthenticator.token_url = os.environ["OAUTH_TOKEN_URL"]
        c.GenericOAuthenticator.userdata_url = os.environ["OAUTH_USERDATA_URL"]

        # Additional Authentik settings
        c.GenericOAuthenticator.userdata_method = "GET"
        c.GenericOAuthenticator.userdata_params = {"scope": "openid email profile"}
        c.GenericOAuthenticator.username_key = "preferred_username"
        c.GenericOAuthenticator.scope = ["openid", "email", "profile"]

    elif auth_type == "GITHUB":
        # Ensure GitHub required variables are provided
        required_vars = ["OAUTH_CALLBACK_URL", "OAUTH_CLIENT_ID", "OAUTH_CLIENT_SECRET"]
        for var in required_vars:
            if not os.environ.get(var):
                raise EnvironmentError(f"{var} environment variable is required for GitHub")

        from oauthenticator.github import GitHubOAuthenticator

        c.JupyterHub.authenticator_class = GitHubOAuthenticator
        c.GitHubOAuthenticator.oauth_callback_url = os.environ["OAUTH_CALLBACK_URL"]
        c.GitHubOAuthenticator.client_id = os.environ["OAUTH_CLIENT_ID"]
        c.GitHubOAuthenticator.client_secret = os.environ["OAUTH_CLIENT_SECRET"]
        c.GitHubOAuthenticator.scope = ['read:org', 'read:user', 'user:email']

    elif auth_type == "GITLAB":
        # For GitLab, additional variable checks can be added if needed.
        from oauthenticator.gitlab import GitLabOAuthenticator

        c.JupyterHub.authenticator_class = GitLabOAuthenticator

    else:
        print("Supported OAUTHENTICATOR values: 'AUTHENTIK', 'GITHUB', 'GITLAB'")
        print("Falling back to native authentication.")
        c.JupyterHub.authenticator_class = "nativeauthenticator.NativeAuthenticator"
        c.NativeAuthenticator.open_signup = True
else:
    # Fallback to native authentication if OAUTHENTICATOR is not set.
    c.JupyterHub.authenticator_class = "nativeauthenticator.NativeAuthenticator"
    c.NativeAuthenticator.open_signup = True


# ================================
# User & Admin Configuration
# ================================

whitelist = set()
admin = set()
userlist_path = os.path.join(_THISDIR, "userlist")

try:
    with open(userlist_path, "r") as f:
        for line in f:
            stripped_line = line.strip()
            if not stripped_line:
                continue
            parts = stripped_line.split()
            username = parts[0]
            whitelist.add(username)
            if len(parts) > 1 and parts[1] in {"admin", "hyradus"}:
                admin.add(username)
except Exception:
    # Fallback to default user if the userlist file is not found or empty
    whitelist.add("jovyan")
    admin.add("jovyan")

# Optionally add an admin from the environment variable
if (admin_env := os.environ.get("JUPYTERHUB_ADMIN")):
    admin.add(admin_env)

c.JupyterHub.admin_access = True
c.Authenticator.admin_users = admin
c.Authenticator.allowed_users = whitelist


# ================================
# Miscellaneous Settings
# ================================

# Set the default interface for user containers
c.Spawner.default_url = "/lab"

# Disable JupyterLab update notifications
c.LabApp.check_for_updates_class = "jupyterlab.NeverCheckForUpdate"
