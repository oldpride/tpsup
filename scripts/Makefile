all: autopath

OBJS := $(wildcard *)

autopath: $(OBJS)
	[ -d ${TPSUP}/autopath ] || mkdir ${TPSUP}/autopath
	/bin/rm -f ${TPSUP}/autopath/*
	cd ${TPSUP}/autopath; \
	pwd; \
	for f in $(OBJS); do ln -s ../scripts/autowrapper $$f; done

