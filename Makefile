ALL := standard-autohealing.yml standard-pet.yml

.PHONY: src

all: ${ALL}

standard-autohealing.yml: src
	ln -fv src/$@ $@

standard-pet.yml: src
	ln -fv src/$@ $@

src:
	$(MAKE) -C $@

clean:
	rm -f ${ALL}
	$(MAKE) -C src clean
