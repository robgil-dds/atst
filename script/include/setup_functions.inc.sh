# setup_functions.inc.sh: Functions used by the setup script

install_pipenv() {
  return_code=0

  # Ensure we are not in a virtual env already
  if [ -z "${VIRTUAL_ENV+is_set}" ]; then
    if ! check_system_pip_for pipenv; then
      # pipenv is not installed, so install it
      echo "Installing pipenv..."
      pip install pipenv
      # Capture pip exit code
      return_code="${?}"
    fi
  fi

  return "${return_code}"
}

check_for_existing_virtual_environment() {
  local python_version="${1}"
  local target_python_version_regex="^Python ${python_version}"

  # Check for existing venv, and if one exists, save the Python version string
  existing_venv_version=$($(pipenv --py 2> /dev/null) --version 2> /dev/null)
  if [ "$?" = "0" ]; then
    # Existing venv; see if the Python version matches
    if [[ "${existing_venv_version}" =~ ${target_python_version_regex} ]]; then
      # Version strings match, valid existing environment is present
      return 0
    fi
  fi

  # No valid virtual environment found
  return 1
}

create_virtual_environment() {
  local python_version="${1}"

  # Create a new virtual environment for the app
  # The environment will be in a directory called .venv off the app
  # root directory
  echo "Creating virtual environment using Python version ${python_version}..."
  PIPENV_VENV_IN_PROJECT=true pipenv --python "${python_version}"
  return $?
}

install_sass() {
  if ! type sass >/dev/null; then
    if type gem >/dev/null; then
      echo 'Installing a sass compiler (gem)...'
      gem install sass
    else
      echo 'Could not install a sass compiler. Please install a version of sass.'
    fi
  fi
}
