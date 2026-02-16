import logging

from zk import ZK
from .models import AttendanceLog
from django.utils.timezone import make_aware, get_current_timezone
from datetime import datetime
logger = logging.getLogger(__name__)
CHECKIN_IPS = [
    '172.16.51.69',
    '172.16.51.53',
    '172.16.51.52',
    '172.16.51.51'
]

CHECKOUT_IPS = [
    '172.16.51.57',
    '172.16.51.56',
    '172.16.51.55',
    '172.16.51.54'
]

ALL_IPS = CHECKIN_IPS + CHECKOUT_IPS

def fetch_and_store_attendance():
    timezone = get_current_timezone()
    total_inserted = 0

    for ip in ALL_IPS:
        zk = ZK(ip, port=4370, timeout=5)
        conn = None
        entry_type = 'IN' if ip in CHECKIN_IPS else 'OUT'

        try:
            logger.info(f"🔗 Connecting to device at {ip} ({entry_type})")
            conn = zk.connect()
            conn.disable_device()

            # ✅ Step 1: Get user list and map user_id to name
            users = conn.get_users()
            user_dict = {str(user.user_id): user.name for user in users}

            latest_log = AttendanceLog.objects.filter(device_ip=ip).order_by('-timestamp').first()
            latest_time = latest_log.timestamp if latest_log else make_aware(datetime.min, timezone)
            latest_time = latest_time.replace(microsecond=0)

            logs = conn.get_attendance()
            inserted = 0

            for log in logs:
                aware_time = make_aware(log.timestamp, timezone).replace(microsecond=0)
                if aware_time > latest_time:
                    user_id = str(log.user_id)
                    user_name = user_dict.get(user_id, '')

                    _, created = AttendanceLog.objects.get_or_create(
                        user_id=user_id,
                        timestamp=aware_time,
                        device_ip=ip,
                        entry_type=entry_type,
                        defaults={
                            'status': log.status,
                            'user_name': user_name
                        }
                    )
                    if created:
                        inserted += 1

            total_inserted += inserted
            logger.info(f"✅ {inserted} new logs saved from {ip} ({entry_type})")

            conn.enable_device()

        except Exception as e:
            logger.info(f"❌ Error with device {ip}: {e}")
            # Add Log and remove pass
            pass

        finally:
            if conn:
                conn.disconnect()

    logger.info(f"🎉 Done. Total logs inserted: {total_inserted}")

SOURCE_IP = '172.16.51.69'
DESTINATION_IPS = [ '172.16.51.57',
    '172.16.51.56',
    '172.16.51.55',
    '172.16.51.54',
    '172.16.51.53',
    '172.16.51.52',
    '172.16.51.51']  # Add more as needed
PORT = 4370

def sync_users_to_multiple_turnstiles():
    source_zk = ZK(SOURCE_IP, port=PORT, timeout=5)
    source_conn = None

    try:
        # Connect to the source device
        source_conn = source_zk.connect()
        source_conn.disable_device()
        source_users = source_conn.get_users()
        logger.info(f"✅ {len(source_users)} users fetched from source: {SOURCE_IP}")

        for dest_ip in DESTINATION_IPS:
            dest_zk = ZK(dest_ip, port=PORT, timeout=5)
            dest_conn = None

            try:
                dest_conn = dest_zk.connect()
                dest_conn.disable_device()

                dest_users = dest_conn.get_users()
                dest_user_ids = {user.user_id for user in dest_users}

                synced_count = 0
                skipped_count = 0

                for user in source_users:
                    if not user.user_id:
                        continue

                    if user.user_id in dest_user_ids:
                        skipped_count += 1
                        continue

                    dest_conn.set_user(
                        uid=user.uid,
                        name=user.name,
                        privilege=user.privilege,
                        password=user.password,
                        group_id=user.group_id,
                        user_id=user.user_id
                    )
                    synced_count += 1

                logger.info(f"📥 {dest_ip} => Synced: {synced_count}, Skipped: {skipped_count}")

                dest_conn.enable_device()
            except Exception as e:
                logger.info(f"❌ Failed to sync to {dest_ip}: {e}")
                 # Add Log and remove pass
                pass
            finally:
                if dest_conn:
                    dest_conn.disconnect()

        source_conn.enable_device()

    except Exception as e:
        logger.info(f"error :{e} ")
        # Add Log and remove pass
        pass
    finally:
        if source_conn:
            source_conn.disconnect()