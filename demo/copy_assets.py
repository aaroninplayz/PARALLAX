import shutil
import glob
import os

src_dir = r"c:\Users\AAron shibu\Desktop\projects\PARALLAX\demo\doc"
dst_dir = r"c:\Users\AAron shibu\Desktop\projects\PARALLAX\demo\frontend\public"

os.makedirs(dst_dir, exist_ok=True)
for file in glob.glob(os.path.join(src_dir, "*.png")):
    print(f"Copying {file} to {dst_dir}")
    shutil.copy(file, dst_dir)

video_src = os.path.join(src_dir, "Project Parallax  Detecting The Invisible.mp4")
video_dst = os.path.join(dst_dir, "hero_video.mp4")
if os.path.exists(video_src):
    print(f"Copying video to {video_dst}")
    shutil.copy(video_src, video_dst)
