"""Bones-Seed X2 clips (joblib pickles) -> plain .npz, so tools/retarget_x2.py can read them without joblib.

Run with a Python that has joblib (not pi/.venv), for example:
    C:/Users/PC/projects/.venvs/mb/Scripts/python.exe -I tools/x2_pkl_to_npz.py OUT_DIR clip1.pkl clip2.pkl ...

Each pickle is {clip_name: {root_trans_offset (T,3), root_rot (T,4) xyzw, dof (T,31) X2 joints in MuJoCo order,
pose_aa, smpl_joints, fps}}. Writes OUT_DIR/<clip_name>.npz with root_pos, root_quat_xyzw, dof, fps.
Bones-Seed data is under its own licence: keep the output local, never commit it.
"""
import os
import sys

import joblib
import numpy as np


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for path in sys.argv[2:]:
        d = joblib.load(path)
        for name, c in d.items():
            np.savez(os.path.join(out, name + '.npz'),
                     root_pos=np.asarray(c['root_trans_offset'], np.float64),
                     root_quat_xyzw=np.asarray(c['root_rot'], np.float64),
                     dof=np.asarray(c['dof'], np.float64),
                     fps=float(c['fps']), source=os.path.basename(path))
            print(name, np.asarray(c['dof']).shape, c['fps'])


if __name__ == '__main__':
    main()
