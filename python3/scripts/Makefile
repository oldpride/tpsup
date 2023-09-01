# gitbash and cygwin cannot use symbolic link reliablely. so we make hard copies

# we don't need to use this Makefile anymore, just run: make_cfg_exec.bash all
# all: old_copy_scripts

all: copy_scripts

copy_scripts:
	make_cfg_exec.bash all

#### the following are old implementation, not neede any more ####

# use relative folder so that we can copy this Makefile to
#    site-spec/python3/scripts 
# and use it there too
TARGET := ../../../tpsup/python3/scripts/tpbatch_py_generic.bash


OBJS := $(wildcard *_cfg.py)


old_copy_scripts: $(OBJS)
	for f in $(OBJS); \
	do \
	   prog=`echo $$f|sed -e 's:_cfg.py::'`; \
           if [ -e $$prog ]; then \
              if [ $$prog -nt $(TARGET) ]; then \
                 echo "skipped $$prog as it is newer than $(TARGET)"; \
                 continue; \
              else \
	         rm -f $$prog; \
              fi; \
           fi; \
           echo "updating $$prog ..."; \
	   cp -f $(TARGET) $$prog; \
	done

