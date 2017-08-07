standard-autohealing.yml: standard-autohealing.template.yml lambda-launcher-dns.mini.py lambda-snapshot-asg.mini.py
	./import-files.py --yaml $< > $@

lambda-launcher-dns.mini.py: lambda-launcher-dns.py
	pyminifier $< > $@

lambda-snapshot-asg.mini.py: lambda-snapshot-asg.py
	pyminifier $< > $@

