#!/bin/sh
#tomcat PID 추출
appPID=$(ps -ef | grep app.py | grep -v grep | grep -v restart | awk '{print $2}')

echo $appPID
if [ "$appPID" = "" ]
then
        nohup /home/ubuntu/myenv/bin/python /home/ubuntu/assi_works/assi_works_app.py >> /home/ubuntu/assi_works/nohup.out 2>&1 &
fi
