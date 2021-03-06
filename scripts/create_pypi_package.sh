#!/bin/bash

if [ $# -lt 2 ]; then
  PYPI=pypitest
else
  PYPI=${2}
fi

if [ $# -lt 1 ]; then
  echo "Usage $0 <lp-path> [<pypi-site>]"
  echo
  echo lp-path: path to linchpin source
  echo 'pypi-site: path to linchpin source (default: pypitest)'
  exit 1
fi

PROMPT=1
LP_PATH=${1}

PKG_TYPES="sdist bdist_wheel"
SETUP_CMD="python setup.py"
CLEAN_CMD="clean"
REG_CMD="register"
UPLOAD_CMD="${PKG_TYPES} upload"

# find extraneous files and remove them
CRUFTIES=('coverage.xml' 'linchpin.log' '*.pyc', '*.retry', '*.sw*')
CRUFTY_DIRS=('linchpin.egg-info' 'build' 'dist' 'docs/build' 'provision/outputs' 'provision/inventories')

echo "REMOVING CRUFTY FILES"

for CRUFT in "${CRUFTIES[@]}"; do
    #echo find ${LP_PATH} -name "${CRUFT}" -delete
    find ${LP_PATH} -name "${CRUFT}" -delete
done

echo
echo "REMOVING CRUFTY DIRS"

for CRUFT_DIR in "${CRUFTY_DIRS[@]}"; do
    #echo rm -rf ${LP_PATH}/${CRUFT_DIR}
    rm -rf ${LP_PATH}/${CRUFT_DIR}
done

CLEAN="${SETUP_CMD} ${CLEAN_CMD}"
REG="${SETUP_CMD} ${REG_CMD} -r ${PYPI}"
UPLOAD="${SETUP_CMD} ${UPLOAD_CMD} -r ${PYPI}"

for ACTION in "${CLEAN}" "${UPLOAD}"; do
    if [ ${PROMPT} -eq 1 ]; then
        echo
        read -p "Run ${ACTION} ([Y]/n)? " yn
        case $yn in
            [Yy]* ) echo "RUNNING ${ACTION}"; ${ACTION};;
            [Nn]* ) echo "EXITING"; exit;;
            * ) echo "RUNNING ${ACTION}"; ${ACTION};;
        esac
    else
        echo "RUNNING ${ACTION}"
        ${ACTION}
    fi
done


#echo ${REG_CMD}
#
#echo ${UPLOAD_CMD}
