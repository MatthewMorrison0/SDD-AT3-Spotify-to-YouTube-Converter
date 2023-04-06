from spotipy.oauth2 import SpotifyOAuth
import webbrowser
from flask import Flask, request, url_for, session, redirect
import requests
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import time
import math

spotify_client_id = '30f5cc799ffc4f1a89a2cdc6f8b0784b'
spotify_client_secret = 'a6d4c157e9e04410b6bf784c26e7ca68'

class YouTubeApiClient():
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/youtubepartner', 'https://www.googleapis.com/auth/youtube', 'https://www.googleapis.com/auth/youtube.force-ssl']
        self.client_secrets_file = 'client_secret_555837191026-lm9sjjlrr1oorltd4sngk8rnvnf9bjkp.apps.googleusercontent.com.json'
        flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, self.scopes)
        flow.run_local_server()
        self.cridentials = flow.credentials
        self.youtube_service = build('youtube', 'v3', credentials=self.cridentials)
    
    def getViedoInfoFromQuery(self, queary): #  Gets top videos on YT from search queary
        request = self.youtube_service.search().list(
        part="snippet",
        q=queary,
        maxResults=1,
        type="video"
        )
        response = request.execute()
        return response
    
    def createPlaylist(self, name):
        request = self.youtube_service.playlists().insert(
            part="snippet",
            body={
            "snippet": {
            "title": name,
                }
            }
        )
        response = request.execute()
        return response
    
    def addSongToPlaylist(self, video_id, playlist_id):
        request = add_video_request=self.youtube_service.playlistItems().insert(
        part="snippet",
        body={
                'snippet': {
                    'playlistId': playlist_id, 
                    'resourceId': {
                        'kind': 'youtube#video',
                        'videoId': video_id
                    }
                }
            }
        )
        response = request.execute()
        return response
        

class SpotifyApiClient():
    def __init__(self): #  Creates spotify OAuth client
        self.sp_oauth = createSpotifyOAuth()
        code = request.args.get('code')
        token_info = self.sp_oauth.get_access_token(code)
        self.access_token = token_info['access_token']
        self.refresh_token = token_info['refresh_token']
        self.token_expires = token_info['expires_at']

    def tokenRefresh(self): #  Refreshes token
        token_info = self.sp_oauth.refresh_access_token(self.refresh_token)
        self.access_token = token_info['access_token']
        self.refresh_token = token_info['refresh_token']
        self.token_expires = token_info['expires_at']

    def getPlaylistInfo(self, playlist_id):
        headers = {
            "Authorization" : f"Bearer {self.access_token}"
        }
        endpoint = 'https://api.spotify.com/v1/playlists/' + playlist_id
        return requests.get(endpoint, headers=headers).json()
    
    def getSongInfoFirstPage(self, spotify_playlist, song_number): #  Gets song of first page (different method to other pages)
        artist_name = spotify_playlist['tracks']['items'][song_number]['track']['album']['artists'][0]['name']
        song_name = spotify_playlist['tracks']['items'][song_number]['track']['name']
        return [song_name, artist_name]

    def getSongInfoSecondPage(self, spotify_playlist, song_number): #  Gets song of next pages
        artist_name = spotify_playlist['items'][song_number]['track']['album']['artists'][0]['name']
        song_name = spotify_playlist['items'][song_number]['track']['name']
        return [song_name, artist_name]
    
    def getNextPlaylistInfo(self, next_url): #  Gets the other pages on playlist info (other than first)
        headers = {
            "Authorization" : f"Bearer {self.access_token}"
        }
        endpoint = next_url
        return requests.get(endpoint, headers=headers).json()
    
    def getSongInfoFirstPage(self, spotify_playlist, song_number): #  Gets song of first page (different method to other pages)
        artist_name = spotify_playlist['tracks']['items'][song_number]['track']['album']['artists'][0]['name']
        song_name = spotify_playlist['tracks']['items'][song_number]['track']['name']
        return [song_name, artist_name]

    def getSongInfoSecondPage(self, spotify_playlist, song_number): #  Gets song of next pages
        artist_name = spotify_playlist['items'][song_number]['track']['album']['artists'][0]['name']
        song_name = spotify_playlist['items'][song_number]['track']['name']
        return [song_name, artist_name]




def main():
    spotify_client = SpotifyApiClient()
    youtube_client = YouTubeApiClient()

    spotify_playlist_id = '2Kx3nUV09qY9W1jCbXFPUP?si=bd55d256a4244b9d&pt=811cbf9318080ec1b780d18c1a3864d7'
    spotify_playlist = spotify_client.getPlaylistInfo(playlist_id=spotify_playlist_id)
    next_url = spotify_playlist['tracks']['next']
    playlist_length = spotify_playlist['tracks']['total']

    youtube_playlist = youtube_client.createPlaylist('Ambient')

    song_index = 0
    page_number = 0
    
    if song_index >= 100: #  Is the first song on the next page?
        spotify_playlist = spotify_client.getNextPlaylistInfo(next_url)
        next_url = spotify_playlist['next']
        playlist_length = spotify_playlist['total']
        page_number += 1

    if playlist_length > 100:
        while song_index < 100: #  Loop that gets songs from playlist and downloads them
            song_info = spotify_client.getSongInfoFirstPage(spotify_playlist, song_index - 100 * page_number)
            video_info = youtube_client.getViedoInfoFromQuery(song_info[0] + " " + song_info[1])
            youtube_client.addSongToPlaylist(video_info['items'][0]['id']['videoId'], youtube_playlist['id'])
            if spotify_client.token_expires < time.time():
                spotify_client.tokenRefresh()

            song_index += 1

        while song_index < playlist_length: #  Loop for pages other than 1
            if song_index % 100 == 0 and next_url != None: #  Gets new page every 100 songs
                spotify_playlist = spotify_client.getNextPlaylistInfo(next_url)
                next_url = spotify_playlist.json()['next']
                playlist_length = spotify_playlist.json()['total']
                page_number += 1

            song_info = spotify_client.getSongInfoSecondPage(spotify_playlist, song_index - 100 * page_number)
            video_info = youtube_client.getViedoInfoFromQuery(song_info[0] + " " + song_info[1])
            youtube_client.addSongToPlaylist(video_info['items'][0]['id']['videoId'], youtube_playlist['id'])
            if spotify_client.token_expires < time.time():
                spotify_client.tokenRefresh()

            song_index += 1
    else:
        while song_index < playlist_length: #  Loop that gets songs from playlist and downloads them
            song_info = spotify_client.getSongInfoFirstPage(spotify_playlist, song_index - 100 * page_number)
            video_info = youtube_client.getViedoInfoFromQuery(song_info[0] + " " + song_info[1])
            youtube_client.addSongToPlaylist(video_info['items'][0]['id']['videoId'], youtube_playlist['id'])
            if spotify_client.token_expires < time.time():
                spotify_client.tokenRefresh()

            song_index += 1
    



app = Flask(__name__)

#  Creates flask application
@app.route('/')
def login():
    sp_oauth = createSpotifyOAuth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/redirect')
def redirectPage():
    main()
    return 'Playlist Converted'

#  Creates spotify Oauth client
def createSpotifyOAuth():
    return SpotifyOAuth(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri=url_for('redirectPage', _external=True),
        scope='user-read-private'
    )

webbrowser.open('http://127.0.0.1:5000') #  Opens site on webbrowser automatically
app.run() #  Runs flask application