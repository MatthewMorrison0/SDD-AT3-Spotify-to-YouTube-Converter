from spotipy.oauth2 import SpotifyOAuth
import webbrowser
from flask import Flask, request, url_for, session, redirect
import requests
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import time


spotify_client_id = '30f5cc799ffc4f1a89a2cdc6f8b0784b' # ID used for Spotify API client
spotify_client_secret = 'a6d4c157e9e04410b6bf784c26e7ca68' # Secret code used for Spotify API client

class YouTubeApiClient(): #YouTube Client 
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/youtubepartner', 'https://www.googleapis.com/auth/youtube', 'https://www.googleapis.com/auth/youtube.force-ssl'] # Scopes that determine what data the YouTube API can access
        self.client_secrets_file = 'client_secret_555837191026-lm9sjjlrr1oorltd4sngk8rnvnf9bjkp.apps.googleusercontent.com.json' # Access .json file that holds client secret data
        # Initiate OAuth 2.0
        flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, self.scopes) 
        flow.run_local_server()
        self.cridentials = flow.credentials
        self.youtube_service = build('youtube', 'v3', credentials=self.cridentials)
    
    def getViedoInfoFromQuery(self, queary): #  Gets top videos on YouTube from search queary
        request = self.youtube_service.search().list(
        part="snippet",
        q=queary,
        maxResults=1,
        type="video"
        )
        response = request.execute()
        return response
    
    def createPlaylist(self, name): # Creates YouTube Playlist with given name on users account
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
    
    def addSongToPlaylist(self, video_id, playlist_id): # Adds a song to the playlist given
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
        

class SpotifyApiClient(): # Spotify Client
    def __init__(self): #  Creates spotify OAuth client
        self.sp_oauth = createSpotifyOAuth() # Initiate OAuth 2.0
        code = request.args.get('code') # Gets varification code that OAuth 2.0 is complete
        token_info = self.sp_oauth.get_access_token(code) # Gets Spotify API token infomation using OAuth 2.0 code
        # Extracts individual tokens from token_info
        self.access_token = token_info['access_token']
        self.refresh_token = token_info['refresh_token']
        self.token_expires = token_info['expires_at']

    def tokenRefresh(self): #  Refreshes token (called when previous one has expired)
        token_info = self.sp_oauth.refresh_access_token(self.refresh_token)
        self.access_token = token_info['access_token']
        self.refresh_token = token_info['refresh_token']
        self.token_expires = token_info['expires_at']

    def getPlaylistInfo(self, playlist_id): # Fetches Spotify playlist given its ID and returns its corresponding .json file
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
    # Create Spotify and YouTube clients
    spotify_client = SpotifyApiClient()
    youtube_client = YouTubeApiClient()

    spotify_playlist_id = '2Kx3nUV09qY9W1jCbXFPUP?si=bd55d256a4244b9d&pt=811cbf9318080ec1b780d18c1a3864d7' # Playlist ID (Only used for testing)
    spotify_playlist = spotify_client.getPlaylistInfo(playlist_id=spotify_playlist_id) # Gets playlist using ID
    next_url = spotify_playlist['tracks']['next'] # Extracts URL for the next page of the playlist (each page only contains at most 100 songs)
    playlist_length = spotify_playlist['tracks']['total'] # Gets playlist length

    youtube_playlist = youtube_client.createPlaylist('Ambient') # Creates playlist on users YouTube account

    song_index = 0
    page_number = 0
    
    if playlist_length > 100: # Goes in to this loop because multiple playlist pages will need to be accessed
        while song_index < 100: #  Loop that gets songs from playlist and downloads them (only for the first page of the playlist)
            song_info = spotify_client.getSongInfoFirstPage(spotify_playlist, song_index) # Gets infomation on song in playlist, indexed by song_index
            video_info = youtube_client.getViedoInfoFromQuery(song_info[0] + " " + song_info[1]) # Search for YouTube video using song name and artist from song_info
            youtube_client.addSongToPlaylist(video_info['items'][0]['id']['videoId'], youtube_playlist['id'])
            # Check if Spotify token has expired and refresh it if it has
            if spotify_client.token_expires < time.time():
                spotify_client.tokenRefresh()

            song_index += 1 # Increment song_index to get next song

        while song_index < playlist_length: #  Loop for pages of the playlist other than 1
            if song_index % 100 == 0 and next_url != None: #  Gets new page every 100 songs
                spotify_playlist = spotify_client.getNextPlaylistInfo(next_url) # URL for the next page of the playlist
                next_url = spotify_playlist.json()['next'] # Prepares new URL for the page after this new one
                playlist_length = spotify_playlist.json()['total'] # Gets playlist length
                page_number += 1

            song_info = spotify_client.getSongInfoSecondPage(spotify_playlist, song_index - 100 * page_number)
            video_info = youtube_client.getViedoInfoFromQuery(song_info[0] + " " + song_info[1])
            youtube_client.addSongToPlaylist(video_info['items'][0]['id']['videoId'], youtube_playlist['id'])
            if spotify_client.token_expires < time.time():
                spotify_client.tokenRefresh()

            song_index += 1
    else:
        while song_index < playlist_length: #  Loop that gets songs from playlist and downloads them
            song_info = spotify_client.getSongInfoFirstPage(spotify_playlist, song_index - 100 * page_number) # Gets song information by offsetting the song index by the number of pages used
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