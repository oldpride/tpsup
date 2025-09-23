import os
import dotenv
import tpsup.envtools

class SiteEnv:
    def __init__(self, **opt):
        debug = opt.get('debug', 0)

        self.sitespec = os.environ.get('SITESPEC', None)
        if not self.sitespec:
            raise RuntimeError("SITESPEC environment variable not set")
        
        # convert to native path, eg, /cygdrive/c/User/tian/... to C:/User/tian/...
        self.sitespec = tpsup.envtools.convert_path(self.sitespec, target='native')
        if not os.path.isdir(self.sitespec):
            raise RuntimeError(f"SITESPEC path not valid: {self.sitespec}")

        if debug:
            print(f"sitespec = {self.sitespec}")
    
    def load_env(self, progname:str, **opt):
        debug = opt.get('debug', 0)

        envfile = f'{self.sitespec}/env/{progname}.env'

        if debug:
            print(f"load_env: expected env file: {envfile}")

        if os.path.isfile(envfile):
            dotenv.load_dotenv(envfile)
        elif debug:
            print(f"Warning: envfile {envfile} not found, skipped loading env file.")

    def get_env(self, varname:str, default=None):
        return os.getenv(varname, default)

def main():
    env = SiteEnv(debug=1)
    env.load_env('ptputty', debug=1)
    print(f"prompt_matured = {env.get_env('prompt_matured')}")

if __name__ == '__main__':
    main()
