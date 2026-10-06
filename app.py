import os
import subprocess
import tempfile
import urllib.request
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)
STORAGE_DIR = "/tmp/videos"
os.makedirs(STORAGE_DIR, exist_ok=True)


@app.route("/render", methods=["POST"])
def render_video():
  data = request.json or {}
  scenes = data.get("scenes", [])
  audio_url = data.get("audio_url")

  with tempfile.TemporaryDirectory() as tmpdir:
    img_paths = []
    for idx, scene in enumerate(scenes):
      img_url = scene.get("image")
      img_file = os.path.join(tmpdir, f"img_{idx}.jpg")
      urllib.request.urlretrieve(img_url, img_file)
      img_paths.append(img_file)

    audio_path = os.path.join(tmpdir, "audio.mp3")
    if audio_url:
      urllib.request.urlretrieve(audio_url, audio_path)

    list_file = os.path.join(tmpdir, "inputs.txt")
    with open(list_file, "w") as f:
      for path in img_paths:
        f.write(f"file '{path}'\n")
        f.write("duration 8\n")
      if img_paths:
        f.write(f"file '{img_paths[-1]}'\n")

    out_filename = f"video_{os.urandom(4).hex()}.mp4"
    out_path = os.path.join(STORAGE_DIR, out_filename)

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_file,
    ]
    if audio_url and os.path.exists(audio_path):
      cmd += ["-i", audio_path, "-c:a", "aac", "-shortest"]

    cmd += [
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-pix_fmt",
        "yuv420p",
        out_path,
    ]

    subprocess.run(cmd, check=True)

    base_url = request.host_url.rstrip("/")
    return jsonify({
        "success": True,
        "video_url": f"{base_url}/download/{out_filename}",
    })


@app.route("/download/<path:filename>")
def download(filename):
  return send_from_directory(STORAGE_DIR, filename)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
