from ConfigParser import ConfigParser
import os
import tempfile
from fabric.colors import red
from fabric.context_managers import hide, cd
from fabric.contrib import files
from fabric.operations import run, put, sudo
from fabric.state import env as _env
from wayly_fabric import _info, _download_remote_file, _success


def config_supervisor(name, **kwargs):
    """
    add supervisor configuration
    """
    _info("Configuring supervisor ... \n")

    temp_path = tempfile.mktemp('.conf')
    parser = ConfigParser()
    conf_path = '/etc/supervisor/conf.d/%s.conf' % name
    project_root = '~/www/%s' % name

    if _download_remote_file(conf_path, temp_path):
        parser.read(temp_path)

    section = 'program:%s' % name
    if not parser.has_section(section):
        parser.add_section(section)

    wsgi_path = ""
    with hide('running', 'stdout'), cd(project_root):
        folders = run('ls -F | grep /')
        for folder in folders.split():
            _path = os.path.join(folder, 'wsgi.py')
            if files.exists(_path):
                wsgi_path = _path.replace('/', '.').strip('.py')
                _info("Found wsgi module: %s \n" % wsgi_path)
                break
        else:
            raise Exception("Can't find wsgi.py when config supervisor and gunicorn")

    command = "/home/%(user)s/env/%(name)s/bin/gunicorn -b unix:/home/%(user)s/run/%(name)s.sock %(wsgi)s:application"\
              % {'user': _env.user, 'name': name, 'wsgi': wsgi_path}

    parser.set(section, 'command', command)
    parser.set(section, 'directory', "/home/%s/www/%s" % (_env.user, name))
    parser.set(section, 'stdout_logfile', "/home/%s/log/%s.log" % (_env.user, name))
    parser.set(section, 'user', 'www-data')
    parser.set(section, 'autostart', 'true')
    parser.set(section, 'autorestart', 'true')
    parser.set(section, 'redirect_stderr', 'true')

    parser.write(open(temp_path, 'w+'))

    _info("Write supervisor config ... \n"),
    put(temp_path, conf_path, use_sudo=True)

    _info("Reloading supervisor ... \n")
    sudo('supervisorctl update')


def env(name, command=None, **kwargs):
    """
    management app environment variables
    `command`:
        `list`: list all env

    fab env:list
    fab env:DATABASE_URL="" add or change env
    """
    remote_path = '/etc/supervisor/conf.d/%s.conf' % name
    local_path = _download_remote_file(remote_path)
    env = {}
    section = 'program:%s' % name
    if local_path:
        parser = ConfigParser()
        parser.read(local_path)
        if parser.has_option(section, 'environment'):
            environ = parser.get(section, 'environment')
            for entry in environ.split(','):
                key, val = entry.split('=')
                env[key] = val
    else:
        raise Exception("Please run config_supervisor first.")

    if command == 'list':
        if not env:
            print red("There is no environment vars now.")

        for key, val in env.items():
            print key, val

    else:
        for key, val in kwargs.items():
            env[key] = val

        parser.set(section, 'environment', ','.join(["%s='%s'" % (k, v) for k, v in env.items()]))
        parser.write(open(local_path, 'w'))
        _info("Updating environment ... \n")
        put(local_path, remote_path, use_sudo=True)

        _info("Reload supervisor ... \n")
        sudo('supervisorctl update')
        _success()


def _supervisor_status(program):
    with hide('running', 'stdout'):
        text = sudo('supervisorctl status %s' % program)
        return text.split()[1]
