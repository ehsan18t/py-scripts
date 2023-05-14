import os
import subprocess
import sys
import shutil
import argparse


# Get download location from command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("dl", help="Download location")
args = parser.parse_args()
dl_location = args.dl

# exit if no args given
if not dl_location:
    print("    - Please enter a download location.")
    sys.exit(1)


def install_packages(required_packages=[], env_name='venv'):
    # Check if the required packages are installed
    not_installed = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            not_installed.append(package)

    # If any required packages are not installed, install them in a local virtual environment
    if not_installed:
        exc_silent([sys.executable, '-m', 'venv', env_name])
        exc_silent(
            [os.path.join(env_name, 'Scripts', 'python'), '-m', 'ensurepip'])
        exc_silent([os.path.join(env_name, 'Scripts', 'pip'),
                   'install', '--upgrade'] + required_packages)


def exc_silent(cmds=[]):
    # Only output if Error
    subprocess.check_call(cmds, stdout=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT)


def run_script(script):
    if os.path.isfile(script):
        subprocess.call([script], shell=True)
    else:
        raise FileNotFoundError(f'{script} script not found in venv/Scripts')


def main():
    # Script Configs
    env_name = 'venv'
    script_file = os.path.join(os.getcwd(), 'downloader.py')
    venv = os.path.join(env_name, 'Scripts', 'python.exe')
    activate_script = os.path.join(env_name, 'Scripts', 'activate.bat')
    deactivate_script = os.path.join(env_name, 'Scripts', 'deactivate.bat')
    required_packages = ["beautifulsoup4", "requests", "tqdm"]

    # Install required packages
    print('- Checking & Installing Packages')
    install_packages(required_packages, env_name)

    # Activate the virtual environment
    print('- Activating VENV')
    run_script(activate_script)

    # Upgrade pip
    print('- Update PIP (if available)')
    exc_silent([venv, '-m', 'pip', 'install', '--upgrade', 'pip'])

    # Run in venv
    print('- Run Script')
    subprocess.call([venv, script_file, dl_location])

    # Deactivate the virtual environment
    print('- Deactivating VENV')
    run_script(deactivate_script)

    # Remove venv after done
    print('- Removing VENV')
    shutil.rmtree(env_name)


main()
