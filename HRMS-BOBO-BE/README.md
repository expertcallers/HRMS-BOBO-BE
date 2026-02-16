````
# commands to start restart uwsgi
# the Django server runs at 9090
cd /root/hrms/HRMS-BOBO-BE

./uwsgi_service.sh start
./uwsgi_service.sh stop
./uwsgi_service.sh restart

# rpm --import https://repo.mysql.com/RPM-GPG-KEY-mysql-2023
# sudo yum install mysql-devel

#both start and restart does the same
````

````
#in windows to activate venv -> Set-ExecutionPolicy RemoteSigned -Scope Process
#https://computingforgeeks.com/how-to-install-python-3-on-centos/
#sudo -u postgres psql
# command = /root/hrms/HRMS-BOBO-BE/venv/bin/daphne -p 9090 hrms.asgi:application
# add in the requirements -> urllib3<2.0
# important python manage.py seed --mode=0011
#install postgresql
$sudo yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-$(rpm -E %rhel)/$(rpm -E %rhel)/pgdg-redhat-repo-latest.noarch.rpm
$yum install postgresql-devel
$sudo yum install postgresql15-server postgresql15-contrib
$sudo /usr/pgsql-15/bin/postgresql-15-setup initdb
$sudo systemctl start postgresql-15
$sudo systemctl enable postgresql-15
$nano ~/.bashrc
$export PATH=/usr/pgsql-15/bin:$PATH
$source ~/.bashrc
$psql --version

# change password
$ sudo -u postgres psql
$ \password postgres
$ \q

$ sudo apt-get update              
$ sudo apt-get install libpq-dev                                                                 

# /var/lib/pgsql/15/data/postgresql.conf
#------------------------------------------------------------------------------
# CONNECTIONS AND AUTHENTICATION
#------------------------------------------------------------------------------
# - Connection Settings -

listen_addresses = '*'


# DUMP postgres database      
$sudo vim  /var/lib/pgsql/<version>/data/pg_hba.conf
# TYPE  DATABASE        USER            ADDRESS                 METHOD
# local   all             all                                     md5
$sudo systemctl restart postgresql-<version>
                        
$export PGPASSWORD='your_password'
$pg_dump -U postgres -w hrms > hrms_dump_nov_24

$psql -U postgres
$drop database hrms;
$create database hrms;
$psql -U db_user db_name < dump_name.sql

                                                                 
$ cd hrms/app
$ python3 -m venv env
$ source env/bin/activate
$ (env) pip install -r requirements.txt

$ (env) python manage.py makemigrations
$ (env) python manage.py migrate
$ (env) python manage.py createsuperuser
````

### supervisor status

````
sudo supervisorctl status
````

### NGROK

````
ngrok http 80
````

#### Loading sqlite database into the postgresql

````
pgloader /home/lohit/workspace/hrms/hrmsdb.sqlite3 postgresql://postgres:postgres@localhost:5432/hrmsdb
````

### create hrms.yml and add the below configurations (alter seckey)m

````
ALLOWED_HOSTS: [ '*' ]
CSRF_TRUSTED_ORIGINS: [ "http://localhost:9002","http://10.30.4.152:9002","http://10.30.4.151:9002","http://10.60.1.68:9002" ]

SEC_KEY: 'django-insecure-0t*$=#fm*f4v%-1=w_qg1p_!460w0+5hozmm42ycfz7ti!!j)m'
DEBUG: True
DEVELOPMENT: True
EMAIL: 'erf@expertcallers.com'
PASSWORD: ''
OPEN_API_KEY: ""
DB_NAME: 'hrms'
DB_PASS: ''
IS_PUBLIC_SERVER: False

EMAIL_ACCOUNTS:
  careers:
    host_user: "careers@expertcallers.com"
    host_password: ""
  erf:
    host_user: "erf@expertcallers.com"
    host_password: ''
````

## run createsuperuser without fail

### Deployment steps

### Edit the conf file of nginx:

````

nano /etc/nginx/nginx.conf

````

#### Add a line in the http, server or location section:

````

client_max_body_size 100M;

````

#### Don't use MB it will not work, only the M!

#### Also do not forget to restart nginx

````

systemctl restart nginx

````

### configure uwsgi

````
#nginx
#proxy_read_timeout 300; # Timeout in seconds for reading a response from the upstream server
#proxy_send_timeout 300; # Timeout in seconds for sending a request to the upstream server

````

##### mysql -u root -p hrms -e "SELECT * FROM ams_leavehistory WHERE date BETWEEN '2023-04-01' AND '2024-01-01'" > leave_history_dump.csv

```
mysql -u root -p

#Create a new user:

CREATE USER 'new_user'@'localhost' IDENTIFIED BY 'password';
CREATE USER 'new_user'@'%' IDENTIFIED BY 'password';

#Grant read access to a database:
GRANT SELECT ON database_name.* TO 'new_user'@'localhost';
GRANT SELECT ON database_name.* TO 'new_user'@'%';

#Flush privileges:
FLUSH PRIVILEGES;
EXIT;

```

# dump lbh

```
#sql_file.sql
SELECT lbh.*, p.emp_id, p.full_name FROM ams_leavebalancehistory lbh JOIN profile p ON lbh.profile_id=p.id
WHERE lbh.date BETWEEN '2023-04-01' AND '2024-04-30'

psql -h localhost -d hrms -U postgres -a -f sql/all_leave_balance_history.sql -o all_lbh.csv

# update query
UPDATE profile SET last_working_day='2024-10-10' WHERE emp_id='12343';
```

# Updated leave balance

```
0 0 1 1 * /home/hk/PycharmProjects/HRMS-BOBO-BE/run_seed.sh lb_for_new_year >> /dev/null 2>&1

```

```
add enable_transport_approval in MiscellaneousMiniFields with boolean yes for transport_approval

```