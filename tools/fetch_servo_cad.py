"""Fetch the servo models that cad/fusion/build.py puts into the Fusion model, into %TEMP%/figrefs. Never into the repo.

  python -I tools/fetch_servo_cad.py

XL330-M288 and its idler: ROBOTIS's models, as published in the Koch v1.1 arm's repository (Apache-2.0 on that repository; ROBOTIS's own terms for them not found: THIRD_PARTY_NOTICES.md).
STS3215 and its passive horn: SO-ARM100's (Apache-2.0).
"""
import os
import urllib.request

ROOT = os.path.join(os.environ['TEMP'], 'figrefs')
KOCH = 'https://raw.githubusercontent.com/jess-moss/koch-v1-1/main/hardware/follower/STEP/'
SO = 'https://raw.githubusercontent.com/TheRobotStudio/SO-ARM100/main/STEP/SO100/'
FILES = {'koch-v1-1/Robotis_DYNAMIXEL_XL330_M288_T.STEP': KOCH + 'Robotis_DYNAMIXEL_XL330_M288_T.STEP',
         'koch-v1-1/Robotis_FPX330_H101.STEP': KOCH + 'Robotis_FPX330_H101.STEP',
         'SO-ARM100/STEP/SO100/STS3215_03a.step': SO + 'STS3215_03a.step',
         'SO-ARM100/STEP/SO100/Passive_Horn_01.step': SO + 'Passive_Horn_01.step',
         # Feetech's own model of the HD-1910-C001, its horns and leads' sockets, linked from the FEETECH wiki's page for the servo. No licence stated: THIRD_PARTY_NOTICES.md
         'feetech-hd1910/HD-1910-C001-20260902.stp': 'https://ftservo.github.io/ftservo-wiki/en/products/models/hd-1910-c001/images/HD-1910-C001-20260902.stp'}
for rel, url in FILES.items():
    p = os.path.join(ROOT, rel)
    if os.path.exists(p):
        print('have', rel)
        continue
    os.makedirs(os.path.dirname(p), exist_ok=True)
    urllib.request.urlretrieve(url, p)
    print('got', rel, os.path.getsize(p))
