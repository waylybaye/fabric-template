from ConfigParser import ConfigParser
import tempfile
from fabric.colors import red, blue
from fabric.context_managers import hide
from fabric.contrib import files
from fabric.operations import  put, sudo, get, os


def config(name, command, virtualenv, **kwargs):
    """
    add supervisor configuration
    """
    print blue("Configuring supervisor ... \n")

    temp_path = tempfile.mktemp('.conf')
    parser = ConfigParser()
    conf_path = '/etc/supervisor/conf.d/%s.conf' % name

    if files.exists(conf_path):
        get(conf_path, temp_path)
        parser.read(temp_path)

    section = 'program:%s' % name
    if not parser.has_section(section):
        parser.add_section(section)


    defaults = {
        'user': 'wwww-data',
        'autostart': 'true',
        'autorestart': 'true',
        'redirect_stderr': 'true',
    }

    defaults.update(kwargs)

    if virtualenv:
        if not command.startswith('/'):
            if files.exists(os.path.join(virtualenv, "bin", command.split()[0])):
                command = os.path.join(virtualenv, "bin", command)

        # defaults['environment'] = 'PATH="%s/bin"' % virtualenv

    parser.set(section, 'command', command)
    for attribute, value in defaults.iteritems():
        parser.set(section, attribute, value)


    parser.write(open(temp_path, 'w+'))

    print blue("Write supervisor config ... \n"),
    put(temp_path, conf_path, use_sudo=True)

    print blue("Reloading supervisor ... \n")
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
    local_path = tempfile.mktemp(".conf")
    get(remote_path, local_path)

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
        print blue("Updating environment ... \n")
        put(local_path, remote_path, use_sudo=True)

        print blue("Reload supervisor ... \n")
        sudo('supervisorctl update')


def _supervisor_status(program):
    with hide('running', 'stdout'):
        text = sudo('supervisorctl status %s' % program)
        return text.split()[1]


def delete(name):
    """Delete supervisor config file"""
    supervisor_config = '/etc/supervisor/conf.d/%s.conf' % name
    if files.exists(supervisor_config):
        print blue("Delete supervisor config file ... \n")
        sudo('rm %s' % supervisor_config)
        sudo('supervisorctl update')


def log(name):
    """show the app wsgi process log"""
    print blue("Getting log for %s" % name)
    with hide('running', 'stdout'):
        msg = sudo('supervisorctl tail %s' % name)
        print msg

