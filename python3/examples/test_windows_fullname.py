import subprocess
import getpass


def get_user_full_name():
    cmd = 'wmic useraccount where name="%username%" get fullname /value'
    # cmd = 'wmic useraccount where name="william" get fullname /value'
    user = getpass.getuser()
    cmd = cmd.replace('%username%', user)
    print(f"cmd={cmd}")

    ps = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = ps.communicate()[0].decode()
    print(f"output={output}")

    # Extract the full name from the output
    full_name = output.strip().split('=')[1]
    return full_name


# Get the current user's full name
full_name = get_user_full_name()
print("Current user's full name:", full_name)
