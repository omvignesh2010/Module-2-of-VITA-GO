from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import whisper
from gtts import gTTS
from deep_translator import GoogleTranslator  
import ffmpeg
import uuid
import traceback

app = Flask(__name__)
CORS(app, resources={r"/upload": {"origins": "*"}, r"/video/*": {"origins": "*"}})

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload():
    model = whisper.load_model("tiny")
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

        # Extract audio
        ffmpeg.input(video_path).output(audio_path, ac=1, ar=16000).run(overwrite_output=True)

        # Transcribe using Whisper
        result = model.transcribe(audio_path)
        original_text = result['text']

        # Translate using deep_translator
        translated_text = GoogleTranslator(source='auto', target=lang).translate(original_text)

        # Text to speech
        tts = gTTS(text=translated_text, lang=lang)
        tts.save(tts_path)

        # Merge new audio with original video
        ffmpeg.output(
            ffmpeg.input(video_path).video,
            ffmpeg.input(tts_path).audio,
            output_video_path,
            vcodec='copy',
            acodec='aac',
            shortest=None
        ).run(overwrite_output=True)

        # Fix: return correct Render URL
        video_url = f"{request.url_root}video/{output_filename}".replace("http://", "https://")

        return jsonify({"video_url": video_url})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/video/<filename>')
def serve_video(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
