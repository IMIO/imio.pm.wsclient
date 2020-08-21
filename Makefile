#!/usr/bin/make
#
all: run

.PHONY: bootstrap
bootstrap:
	virtualenv-2.7 .
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
	rm -fr develop-eggs downloads eggs parts .installed.cfg include lib
