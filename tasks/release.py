# Copyright 2013 Donald Stufft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import datetime
import os
import os.path
import shutil
import tempfile

import invoke
import pkg_resources


@invoke.task
def version():
    """
    Bumps the version in warehouse.__about__
    """
    # Determine the next version number using git tags
    version_series = datetime.datetime.utcnow().strftime("%y.%m")
    version_series = ".".join([str(int(x)) for x in version_series.split(".")])
    tags = invoke.run("git tag -l 'v{}.*'".format(version_series), hide="out")
    versions = sorted(tags.stdout.split(), key=pkg_resources.parse_version)
    version_num = int(versions[-1].rsplit(".")[-1]) + 1 if versions else 0
    version = ".".join([version_series, str(version_num)])
    version = ".".join([str(int(x)) for x in version.split(".")])

    # Determine our build number (It's equal to our current git revision)
    build_tag = invoke.run("git rev-parse HEAD", hide="out").stdout[:7]

    with open("warehouse/__about__.tmpl.py") as tmpl:
        tmpl = tmpl.read()

    with open("warehouse/__about__.py", "w") as about:
        about.write(tmpl.format(version=version, build=build_tag))

    # Commit our new version and tag it
    invoke.run("git add warehouse/__about__.py", hide="out")
    invoke.run(
        "git commit -m 'Generate the release (version={} build={}) "
        "[ci skip]'".format(
            version,
            build_tag,
        ),
        hide="out",
    )
    invoke.run(
        "git tag -m 'Released version v{0} ({1})' v{0}".format(
            version,
            build_tag,
        ),
        hide="out",
    )


@invoke.task
def build():
    """
    Builds the source distribution.
    """
    # Determine what the latest version is
    tags = invoke.run("git tag -l 'v*'", hide="out")
    version = sorted(
        tags.stdout.split(),
        key=pkg_resources.parse_version,
        reverse=True,
    )[0]

    curdir = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    tmpdir = tmpdir if tmpdir.endswith("/") else tmpdir + "/"
    try:
        # Use git archive to export the latest version to a temporary directory
        invoke.run(
            "git archive --format=tar {} | (cd {} && tar xf -)".format(
                version,
                tmpdir,
            ),
        )

        # Change to the temporary directory
        os.chdir(tmpdir)

        # Create our distributions
        os.makedirs("dist")
        for dist_type in ["sdist", "bdist_wheel"]:
            invoke.run("python setup.py {}".format(dist_type))

        # Change back to our normal directory
        os.chdir(curdir)

        # Move the built distributions into our dist directory
        shutil.rmtree(os.path.abspath("dist"), ignore_errors=True)
        shutil.move(
            os.path.join(tmpdir, "dist"),
            os.path.abspath("dist"),
        )
    finally:
        os.chdir(curdir)
        shutil.rmtree(tmpdir, ignore_errors=True)


@invoke.task
def upload():
    invoke.run("twine upload --sign dist/*")


@invoke.task
def development():
    """
    Bumps the version in warehouse.__about__ to a development release
    """
    # Determine the next version number using git tags
    version_series = datetime.datetime.utcnow().strftime("%y.%m")
    version_series = ".".join([str(int(x)) for x in version_series.split(".")])
    tags = invoke.run("git tag -l 'v{}.*'".format(version_series), hide="out")
    versions = sorted(tags.stdout.split(), key=pkg_resources.parse_version)
    version_num = int(versions[-1].rsplit(".")[-1]) + 1 if versions else 0
    version = ".".join([version_series, str(version_num)])
    version = ".".join([str(int(x)) for x in version.split(".")])
    version += ".dev0"

    build_tag = "<development>"

    with open("warehouse/__about__.tmpl.py") as tmpl:
        tmpl = tmpl.read()

    with open("warehouse/__about__.py", "w") as about:
        about.write(tmpl.format(version=version, build=build_tag))

    # Commit our new version and tag it
    invoke.run("git add warehouse/__about__.py", hide="out")
    invoke.run(
        "git commit -m 'Restart development [ci skip]'".format(
            version,
            build_tag,
        ),
        hide="out",
    )


@invoke.task(
    default=True,
    pre=[
        "release.version", "release.build", "release.upload",
        "release.development",
    ],
)
def all():
    pass
