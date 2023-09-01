# gitbash and cygwin cannot use symbolic link reliablely. so we make hard copies


all: copy_scripts

OBJS := $(wildcard *_cfg.py)

copy_scripts: $(OBJS)
	for f in $(OBJS); \
	do \
	   prog=`echo $$f|sed -e 's:_cfg.py::'`; \
           if [ -e $$prog ]; then \
              if [ $$prog -nt tpbatch_py_generic.bash ]; then \
                 echo "skipped $$prog as it is newer than tpbatch_py_generic.bash"; \
                 continue; \
              else \
	         rm -f $$prog; \
              fi; \
           fi; \
           echo "updating $$prog ..."; \
	   cp -f tpbatch_py_generic.bash $$prog; \
	done

