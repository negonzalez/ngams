AUTOMAKE_OPTIONS = 1.8 foreign
DISTCLEANFILES = *~

JAVAROOT = .

CLASSPATH_ENV = CLASSPATH=$$CLASSPATH

data_DATA = ngasapi.jar

datadir = $(prefix)/lib

dist_noinst_JAVA = alma/ngas/client/*.java 

ngasapi_classes = alma/ngas/client/*.class

ngasapi.jar: $(dist_noinst_JAVA)
	cp ../../ngamsData/*.dtd .
	$(JAR) cf ngasapi.jar  $(ngasapi_classes) *.dtd

CLEANFILES = $(ngasapi_classes) *.jar *.dtd

# EOF