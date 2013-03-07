import os
import tempfile
from fabric.api import run, sudo, get, env as _env
from fabric.colors import green, blue, red
from fabric.contrib import files
from fabric.context_managers import cd, prefix, hide
from fabric.contrib.console import confirm
from fabric.utils import fastprint
from wayly_fabric.supervisor import config_supervisor, _supervisor_status


def _success(msg=""):
    print green(msg or "success")


def _info(msg, new_line=False):
    if new_line:
        print blue(msg)
    fastprint(blue(msg))


def _error(msg):
    print red(msg)


def _app_paths(name):
    return "/home/%s/www/%s" % (_env.user, name), "/home/%s/env/%s" % (_env.user, name)


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


def create_app(name=None, git=None):
    """
    Create an app in remote server
    This will create:
        ~/www/app
        ~/env/app
        ~/run/app.sock
    """
    _info("--------- Initialize App ----------\n")

    install_essentials()

    _info("creating folders ... \n")
    # create ~/www directory if not existing
    project_root = '~/www/%s' % name
    if files.exists(project_root):
        raise Exception("the app is already existed.")

    # create base dirs
    _mkdir(['~/run', '~/env', '~/www', '~/log'])

    # change the owner so the gunicorn worker could access it
    sudo('chown www-data:www-data ~/run')

    with hide('running', 'stdout'):
        with cd("~/www"):
            _info("clone git repo ...  \n"),
            run('git clone %s %s' % (git, name))

        with cd("~/env"):
            _info("create virutalenv ... "),
            run("virtualenv %s" % name)
            _success("success")

        with prefix('source ~/env/%s/bin/activate' % name):
            _info("installing gunicorn ... "),
            run('pip install gunicorn')
            _success("success")

    config_supervisor(name)
    start(name)


def _is_package_installed(executable):
    """where a command exists"""
    return run('which ' + executable, quiet=True)


def install_essentials():
    """
    Install essential software:
    supervisor, python-setuptools
    """
    _info("Installing essential packages ... \n")

    if not _is_package_installed("easy_install"):
        with hide('running', 'stdout'):
            print blue("Installing python-setuptools ... "),
            sudo("apt-get install python-setuptools")
            print green("success")

    if not _is_package_installed("supervisorctl"):
        with hide('running', 'stdout'):
            print blue("Installing supervisor ... "),
            sudo('easy_install supervisor')
            print green('success')

    if not _is_package_installed("virtualenv"):
        with hide('running', 'stdout'):
            _info("Installing virtualenv ... "),
            sudo('easy_install virtualenv')
            _success("success")

    if not _is_package_installed("git"):
        with hide('running', 'stdout'):
            print blue('Installing git ... '),
            sudo('apt-get install git')
            print green('success')


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
    project_root, env = _app_paths(name)
    if files.exists(os.path.join(project_root, 'requirements.txt')):
        with cd(project_root), prefix('source %s/bin/activate' % env):
            _info("Installing requirements ... \n")
            run('pip install -r requirements.txt')


def delete_app(name=None):
    project_root = '~/www/%s' % name
    if not files.exists(project_root):
        raise Exception("the app is not existing.")

    if confirm('Are you sure to delete this app( all files will be deleted )?', default=False):
        _info("Delete source files and virtual env ... \n")
        run("rm -rf %s" % project_root)
        run("rm -rf ~/env/%s" % name)

        supervisor_config = '/etc/supervisor/conf.d/%s.conf' % name
        if files.exists(supervisor_config):
            _info("Delete supervisor config file ... \n")
            sudo('rm %s' % supervisor_config)
            sudo('supervisorctl update')

        nginx_config = '/etc/nginx/sites-available/%s.conf' % name
        if files.exists(nginx_config):
            _info("Delete nginx config file ... \n")
            sudo('rm %s' % nginx_config)
            sudo('service nginx reload')


def deploy(name):
    """
    Pull the latest code from remote
    """
    project_root, env = _app_paths(name)
    with cd(project_root):
        run('git pull')

    with cd(project_root), prefix('source %s/bin/activate' % env), hide('running'):
        # initialize the database
        _info("./manage.py syncdb ... \n")
        run('python manage.py syncdb')

        # run south migrations
        _info("./manage.py migrate ... \n")
        run('python manage.py migrate', quiet=True)

        # collect static files
        _info("./manage.py collectstatic --noinput ... \n")
        run('python manage.py collectstatic --noinput')
        start(name)


def start(name):
    """
    Start the wsgi process
    """
    project_root, env = _app_paths(name)
    if _supervisor_status(name).lower() == 'running':
        _error("The app wsgi process is already started.")
        return

    _info("Starting the app wsgi process ... \n")
    sudo('supervisorctl start %s' % name)

    # check if the wsgi process started
    if _supervisor_status(name).lower() == 'running':
        _success()


def stop(name):
    """Stop the wsgi process"""
    if _supervisor_status(name).lower() != 'running':
        _error("The app wsgi process is not running.")
        return

    _info("Stop the app wsgi process ... \n")
    sudo('supervisorctl stop %s' % name)

    if _supervisor_status(name).lower() == 'stopped':
        _success()


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


def log(name):
    """show the app wsgi process log"""
    _info("Getting log for %s\n" % name)
    with hide('running', 'stdout'):
        msg = sudo('supervisorctl tail %s' % name)
        print msg


def hello():
    run("echo Hello")

