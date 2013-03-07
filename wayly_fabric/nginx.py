import tempfile
from fabric.contrib import files
from wayly_fabric import _info
from fabric.api import env, put, run, sudo


def config_nginx(name, host):
    """Config nginx to route requests to wsgi process"""
    template = """
upstream %(app)s_server {
    server unix:/home/%(user)s/run/%(app)s.sock fail_timeout=0;
}

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

        proxy_pass   http://%(app)s_server;
    }

    access_log /var/log/nginx/%(app)s.access.log;
    error_log /var/log/nginx/%(app)s.error.log;
}
    """
    config = template % {
        'user': env.user,
        'app': name,
        'host': host,
    }
    local_path = tempfile.mktemp('.conf')
    with open(local_path, 'w+') as output:
        output.write(config)

    remote_path = "/etc/nginx/sites-available/%s.conf" % name
    link_path = "/etc/nginx/sites-enabled/%s.conf" % name
    _info("Creating nginx config file under sites-available ... \n")
    put(local_path, remote_path, use_sudo=True)
    _info('Linking nginx config file to sites-enabled ... \n')
    if files.exists(link_path):
        sudo('rm %s' % link_path)
    sudo('ln -s %s %s' % (remote_path, link_path))
    _info("Restarting nginx ... \n")
    sudo('service nginx reload')
