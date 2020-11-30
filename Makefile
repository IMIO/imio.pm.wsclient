#!/usr/bin/make
#
all: run

.PHONY: bootstrap
bootstrap:
	if test -f /usr/bin/virtualenv-2.7;then virtualenv-2.7 .;else virtualenv -p python2 .;fi
	bin/python bin/pip install -r https://raw.githubusercontent.com/IMIO/buildout.pm/master/requirements.txt

.PHONY: buildout
buildout:
	if ! test -f bin/buildout;then make bootstrap;fi
	bin/python bin/buildout

.PHONY: run
run:
	if ! test -f bin/instance1;then make buildout;fi
	bin/instance1 fg

.PHONY: cleanall
cleanall:
	rm -fr bin include lib local share develop-eggs downloads eggs parts .installed.cfg
