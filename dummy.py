from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import whisper
from gtts import gTTS
from googletrans import Translator
import ffmpeg
import uuid

app = Flask(__name__)
CORS(app)  # Allow requests from frontend

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

model = whisper.load_model("base")

@app.route('/upload', methods=['POST'])
def upload():
    try:
        video = request.files['video']
        lang = request.form.get('lang')

        if not video or not lang:
            return jsonify({"error": "Missing video or language"}), 400

        uid = uuid.uuid4().hex
        video_filename = f"{uid}.mp4"
        audio_filename = f"{uid}.wav"
        tts_filename = f"{uid}_tts.mp3"
        output_filename = f"{uid}_translated.mp4"
        video_path = os.path.join(UPLOAD_FOLDER, video_filename)
        audio_path = os.path.join(UPLOAD_FOLDER, audio_filename)
        tts_path = os.path.join(UPLOAD_FOLDER, tts_filename)
        output_video_path = os.path.join(OUTPUT_FOLDER, output_filename)
        video.save(video_path)
        ffmpeg.input(video_path).output(audio_path, ac=1, ar=16000).run(overwrite_output=True)
        result = model.transcribe(audio_path)
        original_text = result['text']
        translator = Translator()
        translated_text = translator.translate(original_text, dest=lang).text
        tts = gTTS(text=translated_text, lang=lang)
        tts.save(tts_path)
        ffmpeg.output(
            ffmpeg.input(video_path).video,
            ffmpeg.input(tts_path).audio,
            output_video_path,
            vcodec='copy',
            acodec='aac',
            shortest=None
        ).run(overwrite_output=True)
        video_url = f"http://localhost:5000/video/{output_filename}"
        return jsonify({"video_url": video_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/video/<filename>')
def serve_video(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
