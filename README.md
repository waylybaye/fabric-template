fabric-template
===============


## Simple Template

Including these stacks:

* nginx
* gunicorn
* supervisord


### Usage

```python
# fabfile.py
from fabric_template.templates import simple

def install():
    """Clone remote repo,
    You should set `Deployment Keys` on github or bitbucket if it's private

    This will install these softwares:

    * build-essential
    * python-setuptools
    * python-virtualenv
    * git
    * nginx
    * supervisord
    * wsgi

    And create these folders:
    * ~/www/$name: www root
    * ~/.virtualenvs/$name: for application virtualenv
    * ~/log: for application logs
    """
    simple.create_app('myapp', 'git@github.com:django/djagno-demo.git')

def deploy():
    """
    pull app updates from remote repo and restart server

    This will do:
    * install all packages in `requirements.txt`
    * ./manage.py syncdb
    * ./manage.py migrate
    * ./manage.py collectstatic --no-input
    """
    simple.deploy('myapp')

def status():
    simple.status('myapp')
```
