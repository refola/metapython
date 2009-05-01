#!/bin/bash

VERSION=$1
if [ "$VERSION" == "" ]; then
    echo "You must specify the version to relase"
    exit
fi

python setup.py sdist upload &&
python setup.py bdist_egg upload &&
pushd docs &&
make upload &&
popd &&
pushd ../MetaPython-wiki &&
svn ci -m "Release tutorial for version $VERSION" &&
popd &&
svn cp -m "Branch release $VERSION" https://metapython.googlecode.com/svn/tags/$VERSION https://metapython.googlecode.com/svn/tags/$VERSION