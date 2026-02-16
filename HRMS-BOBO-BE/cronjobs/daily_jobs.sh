cd "/root/hrms/HRMS-BOBO-BE"
. venv/bin/activate
#echo $(which python3)
if [ "$1" = "mark_absent" ]; then
  python manage.py seed --mode="mark_absent"
fi
