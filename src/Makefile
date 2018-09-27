ALL := standard-autohealing.yml standard-pet.yml

PYLINT := pylint --disable=invalid-name,line-too-long,missing-docstring,bad-whitespace

PY_ORIGS := lambda-launcher-dns.py lambda-launcher-eip.py lambda-snapshot-asg.py lambda-snapshot-remover.py
PY_MINIS := ${PY_ORIGS:py=mini.py}

%.mini.py: %.py
	$(PYLINT) --exit-zero $<
	$(PYLINT) -E $<
	pyminifier $< > $@

all: ${ALL}

clean:
	rm -f ${PY_MINIS} ${ALL}

standard-autohealing.yml: standard-autohealing.template.yml lambda-launcher-dns.mini.py lambda-launcher-eip.mini.py lambda-snapshot-asg.mini.py lambda-snapshot-remover.mini.py
	./import-files.py --yaml $< > $@

standard-pet.yml: standard-pet.template.yml lambda-snapshot-instance.mini.py lambda-snapshot-remover.mini.py
	./import-files.py --yaml $< > $@
