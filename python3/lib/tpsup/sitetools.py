import os
import dotenv
import tpsup.envtools

class SiteEnv:
    '''
    provide methods to load site environment files and get env variables.
    '''
    def __init__(self, progname:str, **opt):
        debug = opt.get('debug', 0)

        self.sitespec = os.environ.get('SITESPEC', None)
        self.tpsup = os.environ.get('TPSUP', None)
        self.homedir = tpsup.envtools.get_home_dir()

        self.envfiles =  [ 
            # later files override earlier files
            f'{self.tpsup}/env/{progname}.env', 
            f'{self.sitespec}/env/{progname}.env',
            f'{self.homedir}/.tpsup/env/{progname}.env', 
        ]

        # if not self.sitespec:
        #     raise RuntimeError("SITESPEC environment variable not set")
        
        # # convert to native path, eg, /cygdrive/c/User/tian/... to C:/User/tian/...
        # self.sitespec = tpsup.envtools.convert_path(self.sitespec, target='native')
        # if not os.path.isdir(self.sitespec):
        #     raise RuntimeError(f"SITESPEC path not valid: {self.sitespec}")

        # if debug:
        #     print(f"sitespec = {self.sitespec}")
    
    def load_env(self, **opt):
        debug = opt.get('debug', 0)

        for envfile in self.envfiles:
            envfile = tpsup.envtools.convert_path(envfile, target='native')

            if os.path.isfile(envfile) and os.access(envfile, os.R_OK):
                dotenv.load_dotenv(envfile, override=True) # default is override=False
                if debug:
                    print(f"loaded env file: {envfile}")
            elif debug:
                print(f"Warning: envfile {envfile} not found, skipped loading env file.")

    def get_env(self, varname:str):
        env_var = os.getenv(varname)
        if env_var is None:
            raise RuntimeError(f"{varname} not set in any of the env files: {self.envfiles}")
        return env_var

def main():
    env = SiteEnv('ptputty', debug=1)
    env.load_env(debug=1)
    print(f"siteenv_command={env.get_env('siteenv_command')}")

if __name__ == '__main__':
    main()
