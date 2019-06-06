from flask import Flask, redirect, request, session, url_for, render_template, flash
import requests
import json
import spotipy
from urllib.parse import quote

app = Flask(__name__, static_folder='static', template_folder='templates', instance_relative_config = True)
app.config.from_pyfile('config.py')

secret_key = app.config['SECRET_KEY']
client_id = app.config['CLIENT_ID']
client_secret = app.config['CLIENT_SECRET']

spotify_auth_url = "https://accounts.spotify.com/authorize"
spotify_token_url = "https://accounts.spotify.com/api/token"
spotify_api_base_url = "https://api.spotify.com"
api_version = "v1"
spotify_api_url = "{}/{}".format(spotify_api_base_url, api_version)
redirect_uri='http://localhost:8000/callback'
scope = 'user-library-read user-top-read playlist-modify-public user-follow-read'

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": 'http://localhost:8000/callback',
    "scope": scope,
    "client_id": client_id,
    "show_dialog": "true",
}

@app.route('/')
def auth_page():
    url_args = "&".join(["{}={}".format(key, quote(val)) for key, val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(spotify_auth_url, url_args)
    return redirect(auth_url)

@app.route("/callback")
def callback():
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret,
    }
    post_request = requests.post(spotify_token_url, data=code_payload)
    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    real_token = access_token
    session['real_token'] = real_token
    return redirect(url_for('search'))

@app.route('/search')
def search():
    return render_template('search.html')

@app.route('/get_playlists', methods = ['POST', 'GET'])
def results_of_search():
    tok = session['real_token']
    sp = spotipy.Spotify(auth = tok)
    results = []
    if request.form['location'] == 'local':
        k = sp.current_user_playlists(limit = 50, offset = 0)
        for a in k['items']:
            if a['name'].lower() == request.form['playlist_name'].lower():
                results.append(a)
    else:
        playlists = sp.search(request.form['playlist_name'], limit = 20, offset = 0, type = 'playlist', market = None)
        for thing in playlists['playlists']['items']:
            results.append(thing)
    return render_template('results.html', playlist_options = results)

@app.route('/put_param/<playlist_id>', methods = ['GET', 'POST'])
def get_param(playlist_id):
    return redirect(url_for('pick_features', playlist_id = playlist_id))

@app.route('/audio_features/<playlist_id>')
def pick_features(playlist_id):
    return render_template('home.html', playlist_id = playlist_id)

@app.route('/new_playlist/<playlist_id>', methods = ['POST'])
def get_new_playlist(playlist_id):
    print(request.form)
    new_playlist = []
    values = {}
    checks = ['acousticness_check', 'liveness_check', 'danceability_check', 'speechiness_check', 'tempo_check', 'instrumentalness_check', 'valence_check', 'energy_check']
    values['acousticness'] = float(request.form['acousticness']) / 100.00
    values['liveness'] = float(request.form['liveness']) / 100.00
    values['danceability'] = float(request.form['danceability']) / 100.00
    #values['loudness'] = float(request.form['loudness']) * -1.0
    values['speechiness'] = float(request.form['speechiness']) / 100.00
    values['tempo'] = float(request.form['tempo'])
    values['instrumentalness'] = float(request.form['instrumental']) / 100.00
    values['valence'] = float(request.form['valence']) / 100.00
    values['energy'] = float(request.form['energy']) / 100.00
    for check in checks:
        if check in request.form:
            pass
        else:
            values.pop(check[:-6])
    songs = pull_songs_from_playlist(playlist_id, values)
    if len(songs) == 0:
        error = "No matching songs with these parameters"
        flash('Try again with some different parameters')
        return render_template('home.html', error = error, playlist_id = playlist_id)
    tok = session['real_token']
    sp = spotipy.Spotify(auth = tok)
    username = sp.current_user()['uri'][13:]
    print("....creating playlist")
    user_all_data = sp.current_user()
    user_id = user_all_data['id']
    playlist_all_data = sp.user_playlist_create(user_id, "New Playlist!")
    playlist_id = playlist_all_data["id"]
    sp.user_playlist_add_tracks(user_id, playlist_id, songs)
    playlist_info = sp.user_playlist(user_id, playlist_id = playlist_id)
    new_playlist_link = playlist_info['external_urls']['spotify']
    for item in playlist_info['tracks']['items']:
        new_playlist.append(item)
    return render_template('playlist.html', new_playlist = new_playlist, new_playlist_link = new_playlist_link)

def pull_songs_from_playlist(playlist_id, desired_features):
    res = []
    tok = session['real_token']
    sp = spotipy.Spotify(auth = tok)
    username = sp.current_user()['uri'][13:]
    thing = sp.user_playlist(username, playlist_id)
    for item in thing['tracks']['items']:
        res.append(item['track']['uri'][14:])
    features = sp.audio_features(tracks = res)
    for item in features:
        for feature in desired_features.keys():
            if (item[feature] <= (desired_features[feature] + .35) and item[feature] >= (desired_features[feature] - .35)) or feature == 'tempo':
                if feature == 'tempo':
                    if item[feature] <= desired_features[feature] + 30 and item[feature] >= desired_features[feature] - 30:
                        pass
                    else:
                        id = item['id']
                        res = [x for x in res if x != id]
                        break
            else:
                id = item['id']
                res = [x for x in res if x != id]
                break
    return res


if __name__ == '__main__':
    app.run(host = "localhost", port = 8000, debug = False)
