#!/bin/bash
. /opt/unilidar/setup.bash
[ ! -f /ws/install/setup.bash ] || . /ws/install/setup.bash
exec "$@"
