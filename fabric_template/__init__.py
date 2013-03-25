import json
import os
import tempfile
from fabric.api import run, sudo, get, env as _env
from fabric.colors import green, blue, red
from fabric.contrib import files
from fabric.context_managers import cd, prefix, hide, shell_env
from fabric.contrib.console import confirm
from fabric.utils import fastprint

import supervisor
import nginx

from fabric_template.supervisor import _supervisor_status


__version__ = "0.1.dev1"


def _success(msg=""):
    print green(msg or "success")


def _info(msg):
    if not msg.endswith('\n'):
        msg += "\n"
    fastprint(blue(msg))


def _error(msg):
    print red(msg)


def _app_paths(name):
    return "/home/%s/www/%s" % (_env.user, name), "/home/%s/.virtualenvs/%s" % (_env.user, name)


def _find_main_dir():
    folders = run('ls -F | grep /')
    for folder in folders.split():
        _path = os.path.join(folder, 'wsgi.py')
        if files.exists(_path):
            return folder.strip('/')


def _mkdir(folders):
    """mkdir if not exists"""
    if not type(folders) in [list, tuple]:
        folders = [folders]

    for folder in folders:
        if not files.exists(folder):
            run('mkdir %s' % folder)


def _get_app_config():
    app_config = tempfile.mktemp('.json')
    remote_config = '/home/%s/.app/app.json' % _env.user

    config = {}
    if files.exists(remote_config):
        _download_remote_file(remote_config, app_config)
        config = json.load(open(app_config))

    return config


def _write_app_config(config):
    local_cache = tempfile.mktemp('.json')
    json.dump(config, open(local_cache, 'w'))


def create_app(name=None, git=None):
    """
    Create an app in remote server
    This will create:
        ~/www/app
        ~/env/app
        ~/run/app.sock
    """
    # install essential packages: python-setuptools
    install_essentials()

    env_bas_dir = '/home/%s/.virtualenvs' % _env.user

    # create ~/www directory if not exists
    project_root = '~/www/%s' % name
    if files.exists(project_root):
        print red("The app is already existed.")
        return

    # create base dirs
    _mkdir([env_bas_dir, '~/www', '~/log'])

    home = "/home/%s" % _env.user

    with hide('running', 'stdout'):
        with cd("~/www"):
            _info("git clone %s %s/www/%s ...  \n" % (git, home, name)),
            run('git clone %s %s' % (git, name), pty=False)

        with cd(env_bas_dir):
            _info("create virutalenv %s/%s ... " % (env_bas_dir, name)),
            run("virtualenv %s" % name)

        with prefix('source %s/%s/bin/activate' % (env_bas_dir, name)):
            _info("install gunicorn ... "),
            run('pip install gunicorn')

    install_requirements(name)


def _is_package_installed(executable):
    """where a command exists"""
    return run('which ' + executable, quiet=True)


def install_essentials():
    """
    Install essential software:
    supervisor, python-setuptools
    """
    _info("Installing essential packages ... \n")

    if not _is_package_installed('gcc'):
        print blue("Installing build-essential")
        sudo('apt-get install build-essential')

    if not _is_package_installed("easy_install"):
        print blue("Installing python-setuptools ... "),
        sudo("apt-get install python-setuptools")

    if not _is_package_installed("supervisorctl"):
        print blue("Installing supervisor ... "),
        sudo('easy_install supervisor')

    if not _is_package_installed("virtualenv"):
        _info("Installing virtualenv ... "),
        sudo('easy_install virtualenv')

    if not _is_package_installed("git"):
        print blue('Installing git ... '),
        sudo('apt-get install git')


def _download_remote_file(remote_path, local_path="", hide_message=False):
    if not local_path:
        local_path = tempfile.mktemp('.conf')

    if files.exists(remote_path, use_sudo=True):
        if not hide_message:
            _info("Found existed supervisor conf file, downloading ... ")
        with hide('running', 'stdout'):
            get(remote_path, local_path)
        if not hide_message:
            _success()
        return local_path


def install_requirements(name):
    """
    run `pip install -r requirements`
    """
    project_root, env = _app_paths(name)
    if files.exists(os.path.join(project_root, 'requirements.txt')):
        with cd(project_root), prefix('source %s/bin/activate' % env):
            _info("Installing requirements ... \n")
            run('pip install -r requirements.txt')


def delete_app(name=None):
    """"""
    project_root = '~/www/%s' % name
    if not files.exists(project_root):
        print red("the app is not existing.")
        return

    if confirm('Are you sure to delete this app( all files will be deleted )?', default=False):
        _info("Delete source files and virtual env ... \n")
        run("rm -rf %s" % project_root)
        run("rm -rf ~/env/%s" % name)


def deploy(name):
    """
    Pull the latest code from remote
    """
    project_root, env = _app_paths(name)
    with cd(project_root):
        run('git pull', pty=False)

    environ = supervisor._get_environment(name)

    with cd(project_root), prefix('source %s/bin/activate' % env), hide('running'), shell_env(**environ):
        install_requirements(name)

        # initialize the database
        _info("./manage.py syncdb ... \n")
        run('python manage.py syncdb')

        # run south migrations
        _info("./manage.py migrate ... \n")
        run('python manage.py migrate', quiet=True)

        # collect static files
        _info("./manage.py collectstatic --noinput ... \n")
        run('python manage.py collectstatic --noinput')
        supervisor.restart(name)


def status(name=""):
    """
    check the process status
    """
    _info("Checking service status ... \n")
    with hide('running', 'stdout'):
        print blue('nginx    :'), sudo('service nginx status')

        text = sudo('supervisorctl status %s' % name)
        gunicorn_status = text.split()[1]
        extra_msg = ""

        if gunicorn_status.lower() == 'running':
            extra_msg = " ".join(text.split()[2:])

        print blue('gunicorn :'), gunicorn_status, extra_msg



def hello():
    run("echo Hello")
