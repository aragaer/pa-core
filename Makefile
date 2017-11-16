PYTHON_MODULES := pa2human router tg

run:
	./run.sh

niege:
	-./main.py --name Niege

lexi:
	-./main.py --incoming incoming --no-translator --name Lexi

update: $(addprefix UPDATE_, $(PYTHON_MODULES)) UPDATE_core

UPDATE_core:
	@echo updating core
	.env/bin/pip3 install -U -r requirements.txt

UPDATE_%:
	@echo updating $*
	cd $*; .env/bin/pip3 install -U -r requirements.txt
