from flask import Flask, request, render_template_string, send_file, url_for
import os
import whisper
from gtts import gTTS
from googletrans import Translator
import ffmpeg
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load Whisper model
model = whisper.load_model("base")

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Module 2 of VITA-GO</title>
</head>
<body>
    <h2>Upload Video for Translation</h2>
    <form method="POST" enctype="multipart/form-data">
        <label>Video File:</label><br>
        <input type="file" name="video" required><br><br>

        <label>Target Language:</label><br>
        <select name="lang" required>
            <option value="ta">Tamil</option>
            <option value="hi">Hindi</option>
            <option value="te">Telugu</option>
            <option value="ml">Malayalam</option>
            <option value="kn">Kannada</option>
            <option value="bn">Bengali</option>
            <option value="gu">Gujarati</option>
            <option value="pa">Punjabi</option>
            <option value="mr">Marathi</option>
            <option value="en">English</option>
        </select><br><br>

        <input type="submit" value="Translate & Dub">
    </form>

    {% if video_url %}
    <h3>Translated Video</h3>
    <video width="640" height="360" controls>
        <source src="{{ video_url }}" type="video/mp4">
        Your browser does not support the video tag.
    </video>
    {% endif %}
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    video_url = None

    if request.method == 'POST':
        video = request.files['video']
        lang = request.form.get('lang')

        if not video:
            return "No video uploaded."

        uid = uuid.uuid4().hex
        video_path = os.path.join(UPLOAD_FOLDER, f"{uid}.mp4")
        audio_path = os.path.join(UPLOAD_FOLDER, f"{uid}.wav")
        tts_path = os.path.join(UPLOAD_FOLDER, f"{uid}_tts.mp3")
        output_video = os.path.join(OUTPUT_FOLDER, f"{uid}_translated.mp4")

        # Save video
        video.save(video_path)

        # Extract audio
        ffmpeg.input(video_path).output(audio_path, ac=1, ar=16000).run(overwrite_output=True)

        # Transcribe
        result = model.transcribe(audio_path)
        original_text = result['text']

        # Translate
        translator = Translator()
        translated = translator.translate(original_text, dest=lang).text

        # TTS
        tts = gTTS(text=translated, lang=lang)
        tts.save(tts_path)

        # Merge new audio
        ffmpeg.output(
            ffmpeg.input(video_path).video,
            ffmpeg.input(tts_path).audio,
            output_video,
            vcodec='copy',
            acodec='aac',
            shortest=None
        ).run(overwrite_output=True)

        video_url = url_for('static', filename=os.path.basename(output_video))
        return render_template_string(HTML, video_url=video_url)

    return render_template_string(HTML, video_url=None)

@app.route('/static/<filename>')
def static_video(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename))

if __name__ == '__main__':
    app.run(debug=True)
