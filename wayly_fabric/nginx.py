import os
import tempfile
from fabric.colors import blue
from fabric.contrib import files
from fabric.api import env, put, sudo


_prefix = "/etc/init.d/nginx"
_conf_prefix = '/etc/nginx/sites-available'


def reload():
    return sudo('%s reload' % _prefix)


def start():
    return sudo('%s start' % _prefix)


def stop():
    return sudo('%s stop' % _prefix)


def config(name, host, proxy):
    """Config nginx to route requests to wsgi process"""
    template = """
server {
    listen 80 default;
    client_max_body_size 4G;
    server_name %(host)s;

    keepalive_timeout 5;

    # path for static files
    # root /path/to/app/current/public;

    location / {
        # checks for static file, if not found proxy to app
        try_files $uri @proxy_to_app;
    }

    location @proxy_to_app {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;

        proxy_pass %(proxy)s;
    }

    access_log /var/log/nginx/%(app)s.access.log;
    error_log /var/log/nginx/%(app)s.error.log;
}
    """
    config = template % {
        'app': name,
        'user': env.user,
        'host': host,
        'proxy': proxy,
    }

    local_path = tempfile.mktemp('.conf')
    with open(local_path, 'w+') as output:
        output.write(config)

    remote_path = "/etc/nginx/sites-available/%s.conf" % name
    link_path = "/etc/nginx/sites-enabled/%s.conf" % name
    print blue("Creating nginx config file under sites-available ... \n")
    put(local_path, remote_path, use_sudo=True)

    print blue('Linking nginx config file to sites-enabled ... \n')
    if files.exists(link_path):
        sudo('rm %s' % link_path)
    sudo('ln -s %s %s' % (remote_path, link_path))

    print blue("Restarting nginx ... \n")
    sudo('service nginx reload')


def delete(name):
    """Delete nginx config"""
    config_files= [
        os.path.join(_conf_prefix, '%s.conf' % name),
        '/etc/nginx/sites-enabled/%s.conf' % name,
    ]

    for file_path in config_files:
        if files.exists(file_path):
            sudo('rm %s' % file_path)
