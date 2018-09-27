ALL := standard-autohealing.yml standard-pet.yml

.PHONY: src

all: ${ALL}

standard-autohealing.yml: src
	ln -s src/$@ $@

standard-pet.yml: src
	ln -s src/$@ $@

src:
	$(MAKE) -C $@

clean:
	rm -f ${ALL}
	$(MAKE) -C src clean
