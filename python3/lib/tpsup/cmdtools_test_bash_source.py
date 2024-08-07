import subprocess
import pprint

cmd = [ 'C:/Program Files/Git/bin/bash.exe',
       "-c",
       "source $HOME/sitebase/github/tpsup/python3/lib/tpsup/cmdtools_test_bash_source.bash"
    #    "source cmdtools_test_bash_source.bash"
]

proc = subprocess.run(cmd,
                        shell=True,  # this allows to run multiple commands
                        capture_output=True,
                        text=True)
ret = {
    'rc': proc.returncode,
    'stdout': proc.stdout,
    'stderr': proc.stderr,
}

pprint.pprint(ret)
