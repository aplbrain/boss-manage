nodesource-repo:
  pkgrepo.managed:
    - humanname: nodesource
    - name: deb https://deb.nodesource.com/node_5.x trusty main
    - file: /etc/apt/sources.list.d/nodesource.list
    - key_url: https://deb.nodesource.com/gpgkey/nodesource.gpg.key

nodejs:
  pkg.installed:
    - fromrepo: trusty
    - version: 5.4.1-1nodesource1~trusty1

npm@3.5.3:
  npm.installed:
    - require:
      - pkg: nodejs

bower@1.7.3:
  npm.installed:
    - require:
      - pkg: nodejs

gulp@3.9.0:
  npm.installed:
    - require:
      - pkg: nodejs
