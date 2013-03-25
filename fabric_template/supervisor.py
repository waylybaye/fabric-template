from ConfigParser import ConfigParser
import tempfile
from fabric.colors import red, blue, green
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


def _get_environment(name):
    """
    Get user custom environment variables
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

                # remove start and trailing quotes
                if val[0] in ['"', "'"] and val[0] == val[-1]:
                    val = val.strip(val[0])

                env[key] = val

    return env


def _set_environment(name, **kwargs):
    """
    set user custom environment variables
    """
    remote_path = '/etc/supervisor/conf.d/%s.conf' % name
    local_path = tempfile.mktemp(".conf")
    get(remote_path, local_path)

    parser = ConfigParser()
    parser.read(local_path)
    section = 'program:%s' % name
    parser.set(section, 'environment', ','.join(['%s="%s"' % (k, v) for k, v in kwargs.iteritems()]))
    parser.write(open(local_path, 'w'))
    print blue("Updating environment ... \n")
    put(local_path, remote_path, use_sudo=True)

    print blue("Reload supervisor ... \n")
    sudo('supervisorctl update')


def env(name, command=None, **kwargs):
    """
    management app environment variables
    `command`:
        `list`: list all env

    fab env:list
    fab env:DATABASE_URL="" add or change env
    """

    env = _get_environment(name)

    if command == 'list':
        if not env:
            print red("There is no environment vars now.")

        for key, val in env.items():
            print blue("%-15s = %s" % (key, val))

    else:
        _set_environment(name, **kwargs)


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



def start(name):
    """
    Start the wsgi process
    """
    if _supervisor_status(name).lower() == 'running':
        print red("The app wsgi process is already started.")
        return

    print blue("Starting the app wsgi process ... ")
    sudo('supervisorctl start %s' % name)

    # check if the wsgi process started
    if _supervisor_status(name).lower() == 'running':
        print green("success")


def stop(name):
    """Stop the wsgi process"""
    if _supervisor_status(name).lower() != 'running':
        print red("The app wsgi process is not running.")
        return

    print blue("Stop the app wsgi process ... ")
    sudo('supervisorctl stop %s' % name)

    if _supervisor_status(name).lower() == 'stopped':
        print green("success")


def restart(name):
    sudo('supervisorctl restart %s' % name)
