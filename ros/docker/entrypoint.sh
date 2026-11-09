#!/bin/bash
. /opt/unilidar/setup.bash
. /opt/slam/setup.bash
[ ! -f /ws/install/setup.bash ] || . /ws/install/setup.bash
exec "$@"
