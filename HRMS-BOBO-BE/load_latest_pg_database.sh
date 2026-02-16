#!/bin/bash

# PostgreSQL superuser credentials
PG_USER="postgres"
export PGPASSWORD="Ecplhrms"
# Log in to PostgreSQL and execute commands
psql -U "$PG_USER" -d postgres -c "DROP DATABASE IF EXISTS hrms;"
psql -U "$PG_USER" -d postgres -c "CREATE DATABASE hrms;"
psql -U "$PG_USER" -w hrms < hrms_dump_latest #local_data_dump
