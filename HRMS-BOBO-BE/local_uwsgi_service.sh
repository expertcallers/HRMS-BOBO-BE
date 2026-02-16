#!/bin/bash

WORK_DIR="/home/lohit/PycharmProjects/HRMS-BOBO-BE"
#WORK_DIR="/root/hrms/HRMS-BOBO-BE"
# Path to the uwsgi executable

UWSGI_EXECUTABLE="$WORK_DIR/venv/bin/uwsgi"

# Path to the uwsgi configuration file
UWSGI_CONFIG_FILE="$WORK_DIR/local_uwsgi.ini"

LOG_DIR="$WORK_DIR/loguwsgi"
MAX_LOG_SIZE=3  # Maximum log file size
# Path to the log file
LOG_FILE="$LOG_DIR/uwsgi.log"

# Path to the pid file
PID_DIR="$WORK_DIR/PID"

# Function to start the uWSGI service
start_uwsgi() {
    mkdir -p $PID_DIR
    $UWSGI_EXECUTABLE --ini $UWSGI_CONFIG_FILE --daemonize=$LOG_FILE --pidfile=$PID_DIR/uwsgi.pid
}

# Function to stop the uWSGI service
stop_uwsgi() {
    $UWSGI_EXECUTABLE --stop $PID_DIR/uwsgi.pid
    rm -f $PID_DIR/uwsgi.pid
}

# Check if log directory exists, if not create it
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
fi

# Get the current user's username
current_user=$(whoami)

# Get the current user's primary group
user_group=$(id -gn $current_user)

# ...

# Check log size and rotate if necessary
check_log_size() {
    if [ -f "$LOG_FILE" ]; then
        size=$(du -b "$LOG_FILE" | cut -f1)
        if [ $size -ge $((MAX_LOG_SIZE *1024 * 1024)) ]; then
            mv "$LOG_FILE" "$LOG_FILE.$(date +'%Y%m%d%H%M%S').old"
            touch "$LOG_FILE"
            chown :"$user_group" "$LOG_FILE"  # Adjust ownership using the user's group
            chmod 644 "$LOG_FILE"  # Adjust permissions as needed
        fi
    fi
}


# Parse command-line arguments
case "$1" in
    start)
        stop_uwsgi
        sleep 3
        start_uwsgi
        ;;
    stop)
        stop_uwsgi
        ;;
    restart)
        stop_uwsgi
        sleep 3
        start_uwsgi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
        ;;
esac
check_log_size


exit 0
