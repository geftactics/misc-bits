#!/bin/bash

# Quick-n-dirty cloud-init script to configure an AWS EC2 instance to run LibreTime software
# We mount an EBS volume, which contains database backup, which we restore from.

export DEBIAN_FRONTEND=noninteractive;
export COMPOSER_HOME=/tmp

# Get fresh
apt-get update
apt-get upgrade -y
apt-get install awscli -y
timedatectl set-timezone Europe/London

# Mount and configure EBS volume
instanceid=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
aws ec2 detach-volume --volume-id vol-0e18f34cbbea8ced8 --region eu-west-1
sleep 10 # yuck
aws ec2 attach-volume --volume-id vol-0e18f34cbbea8ced8 --instance-id $instanceid --device /dev/xvdf --region eu-west-1
mkdir /srv/airtime
echo "UUID=a0851a45-2393-4314-b3ac-6acee9a37ea9  /srv/airtime    ext4    defaults,nofail        0    2" >> /etc/fstab
sleep 10 # yuck
mount UUID=a0851a45-2393-4314-b3ac-6acee9a37ea9  /srv/airtime
chown www-data:www-data /srv/airtime

# Install Libretime
wget https://github.com/LibreTime/libretime/releases/download/3.0.0-alpha.8/libretime-3.0.0-alpha.8.tar.gz -O /root/libretime-3.0.0-alpha.8.tar.gz
tar -zxvf /root/libretime-3.0.0-alpha.8.tar.gz -C /root
cd /root/libretime-3.0.0-alpha.8
./install -fiap
sleep 15 # yuck

# Enable auto backup to EBS volume
echo "sudo -u postgres pg_dumpall | gzip -c > /srv/airtime/libretime-backup.gz" > /etc/cron.daily/libretime-db-backup
echo "cp /etc/airtime/airtime.conf /srv/airtime/airtime.conf" >> /etc/cron.daily/libretime-db-backup
chmod +x /etc/cron.daily/libretime-db-backup

# Restore DB and config
cp /srv/airtime/airtime.conf /etc/airtime/airtime.conf
cp /srv/airtime/libretime-backup.gz /tmp
sudo -u postgres dropdb airtime
rm -f /tmp/libretime-backup
gunzip /tmp/libretime-backup.gz
sudo -u postgres psql -f /tmp/libretime-backup

# Start services
service airtime-playout start
service airtime-liquidsoap start
service airtime_analyzer start
service airtime-celery start
