import os
from flask import Flask, send_from_directory, jsonify, abort

app = Flask(__name__)
GIF_FOLDER = '/home/saltchicken/remote/output'

@app.route('/')
def index():
    return open('index.html').read()

@app.route('/gifs')
def list_gifs():
    files = [f for f in os.listdir(GIF_FOLDER) if f.lower().endswith('.gif')]
    return jsonify(files)

@app.route('/gifs/<path:filename>')
def get_gif(filename):
    return send_from_directory(GIF_FOLDER, filename)

@app.route('/delete/<path:filename>', methods=['DELETE'])
def delete_gif(filename):
    safe_path = os.path.normpath(os.path.join(GIF_FOLDER, filename))
    print(safe_path)
    print(os.path.abspath(GIF_FOLDER))
    if not safe_path.startswith(os.path.abspath(GIF_FOLDER)):
        print("TRhis is bad")
        abort(400, "Invalid file path")
    try:
        os.remove(safe_path)
        os.remove(safe_path.replace('.gif', '.png'))
        return '', 204
    except FileNotFoundError:
        return abort(404, "File not found")
    except Exception as e:
        return abort(500, f"Error deleting file: {e}")

if __name__ == '__main__':
    app.run(debug=True)
