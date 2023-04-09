from spotipy.oauth2 import SpotifyOAuth
import webbrowser
from flask import Flask, request, url_for, session, redirect, render_template
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
import time


spotify_client_id = '30f5cc799ffc4f1a89a2cdc6f8b0784b' # ID used for Spotify API client
spotify_client_secret = 'a6d4c157e9e04410b6bf784c26e7ca68' # Secret code used for Spotify API client
spotify_playlist_id = 'NULL'
youtube_playlist_url = 'NULL'
playlist_converted = False
spotify_playlist = {}
page_history = []



class YouTubeApiClient(): #YouTube Client 
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/youtubepartner', 
                       'https://www.googleapis.com/auth/youtube', 
                       'https://www.googleapis.com/auth/youtube.force-ssl'] # Scopes that determine what data the YouTube API can access
        self.client_secrets_file = 'client_secret_555837191026-lm9sjjlrr1oorltd4sngk8rnvnf9bjkp.apps.googleusercontent.com.json' # Access .json file that holds client secret data
        # Initiate OAuth 2.0
        flow = InstalledAppFlow.from_client_secrets_file(self.client_secrets_file, self.scopes) 
        flow.run_local_server()
        self.cridentials = flow.credentials
        self.youtube_service = build('youtube', 'v3', credentials=self.cridentials)
    
    def getViedoInfoFromQuery(self, queary): #  Gets top videos on YouTube from search queary
        print(queary)
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
            part="snippet, status",
            body={
            "snippet": {
                "title": name 
            },
            "status": {
                "privacyStatus": "public"
            }
            }
        )
        response = request.execute()
        return response
    
    def addSongToPlaylist(self, video_id, playlist_id): # Adds a song to the playlist given
        max_retries = 5
        retry_count = 0
        backoff_time = 1  # In seconds

        # Sometimes, the attempt to add a song to a playlist fails. This allows for this faliure and retrys later
        while retry_count < max_retries:
            try: # Try to add song
                request = self.youtube_service.playlistItems().insert(
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
            except HttpError as e: # If it fails:
                if e.resp.status == 409 and 'SERVICE_UNAVAILABLE' in str(e):
                    retry_count += 1
                    print(f"Attempt {retry_count} failed. Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    backoff_time *= 2  # Exponential backoff
                else:
                    raise
        raise Exception("Failed to add the song to the playlist after multiple retries.")
        

class SpotifyApiClient(): # Spotify Client
    def __init__(self): #  Creates spotify OAuth client
        self.sp_oauth = createSpotifyOAuth() # Initiate OAuth 2.0
        code = request.args.get('code') # Gets varification code that OAuth 2.0 is complete
        token_info = self.sp_oauth.get_access_token(code) # Gets Spotify API token information using OAuth 2.0 code
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
    
    def getUsersPlaylists(self, user_id, offset): # Returns playlist that the user has created (public only)
        headers = {
            "Authorization" : f"Bearer {self.access_token}"
        }
        endpoint = 'https://api.spotify.com/v1/users/' + user_id + '/playlists?offset=' + str(offset) + '&limit=50'
        return requests.get(endpoint, headers=headers).json()
    
    def getUser(self): # Gets information on user logged in
        headers = {
            "Authorization" : f"Bearer {self.access_token}"
        }
        endpoint = 'https://api.spotify.com/v1/me'
        return requests.get(endpoint, headers=headers).json()



def fetchUserData(): # Get user data ready for the home page
    # Create Spotify and YouTube clients
    global spotify_client
    spotify_client = SpotifyApiClient()
    global youtube_client
    youtube_client = YouTubeApiClient()

    user_id = spotify_client.getUser()['id']
    user_playlists_info = spotify_client.getUsersPlaylists(user_id, 0)
    global user_playlists
    user_playlists = []
    playlist_index = 0
    # Create list of all the IDs and names of the playlists the user has
    while playlist_index < len(user_playlists_info['items']):
        user_playlists.append({'id': user_playlists_info['items'][playlist_index]['id'], 'name': user_playlists_info['items'][playlist_index]['name']})
        playlist_index += 1
    while user_playlists_info['next'] != None:
        user_playlists_info = spotify_client.getUsersPlaylists(user_id, user_playlists_info['offset'] + 50)
        playlist_index = 0
        while playlist_index < len(user_playlists_info['items']):
            user_playlists.append({'id': user_playlists_info['items'][playlist_index]['id'], 'name': user_playlists_info['items'][playlist_index]['name']})
            playlist_index += 1


def main():
    global spotify_playlist_id
    global spotify_client
    global youtube_client
    global youtube_playlist_url
    global playlist_converted
    global spotify_playlist
    if playlist_converted == False:
        if spotify_playlist_id == '': # If user nothing for the playlist ID
            return # return from main()
        spotify_playlist = spotify_client.getPlaylistInfo(playlist_id=spotify_playlist_id) # Gets playlist using ID
        if 'error' in spotify_playlist:
            return # return from main()
        next_url = spotify_playlist['tracks']['next'] # Extracts URL for the next page of the playlist (each page only contains at most 100 songs)
        playlist_length = spotify_playlist['tracks']['total'] # Gets playlist length

        youtube_playlist = youtube_client.createPlaylist(spotify_playlist['name']) # Creates playlist on users YouTube account with same name as Spotify playlist
        youtube_playlist_url = 'https://www.youtube.com/playlist?list=' + youtube_playlist['id']

        song_index = 0
        page_number = 0
        
        if playlist_length > 100: # Goes in to this loop because multiple playlist pages will need to be accessed
            while song_index < 100: #  Loop that gets songs from playlist and downloads them (only for the first page of the playlist)
                song_info = spotify_client.getSongInfoFirstPage(spotify_playlist, song_index) # Gets information on song in playlist, indexed by song_index
                video_info = youtube_client.getViedoInfoFromQuery(song_info[0] + " - " + song_info[1]) # Search for YouTube video using song name and artist from song_info
                youtube_client.addSongToPlaylist(video_info['items'][0]['id']['videoId'], youtube_playlist['id']) # Addes song video found by search to YouTube playlist
                # Check if Spotify token has expired and refresh it if it has
                if spotify_client.token_expires < time.time():
                    spotify_client.tokenRefresh()

                song_index += 1 # Increment song_index to get next song

            while song_index < playlist_length: #  Loop for pages of the playlist other than 1
                if song_index % 100 == 0 and next_url != None: #  Gets new page every 100 songs
                    spotify_playlist = spotify_client.getNextPlaylistInfo(next_url) # URL for the next page of the playlist
                    next_url = spotify_playlist['next'] # Prepares new URL for the page after this new one
                    playlist_length = spotify_playlist['total'] # Gets playlist length
                    page_number += 1 # Increment page number

                song_info = spotify_client.getSongInfoSecondPage(spotify_playlist, song_index - 100 * page_number) # Gets song information by offsetting the song_index by the number of pages used
                video_info = youtube_client.getViedoInfoFromQuery(song_info[0] + " " + song_info[1]) # Search for YouTube video using song name and artist from song_info
                youtube_client.addSongToPlaylist(video_info['items'][0]['id']['videoId'], youtube_playlist['id']) # Addes song video found by search to YouTube playlist
                # Check if Spotify token has expired and refresh it if it has
                if spotify_client.token_expires < time.time():
                    spotify_client.tokenRefresh()

                song_index += 1 # Increment song_index
        else: # If playlist_length <= 100, only one page will need to be accessed
            while song_index < playlist_length: #  Loop that gets songs from playlist and downloads them
                song_info = spotify_client.getSongInfoFirstPage(spotify_playlist, song_index) # Gets song information
                video_info = youtube_client.getViedoInfoFromQuery(song_info[0] + " " + song_info[1]) # Search for YouTube video using song name and artist from song_info
                youtube_client.addSongToPlaylist(video_info['items'][0]['id']['videoId'], youtube_playlist['id']) # Addes song video found by search to YouTube playlist
                # Check if Spotify token has expired and refresh it if it has
                if spotify_client.token_expires < time.time():
                    spotify_client.tokenRefresh()

                song_index += 1 # Increment song_index
        playlist_converted = True
    else:
        return
    



#  Creates flask application
app = Flask(__name__)

@app.route('/')
def login():
    # Create Spotify OAuth to get redirect page
    sp_oauth = createSpotifyOAuth()
    auth_url = sp_oauth.get_authorize_url()

    return redirect(auth_url) # Go to redirect page given by Spotify

@app.route('/redirect', methods=['GET', 'POST'])
def redirectPage(): # Shows loading screen for users data
    global page_history
    page_history.append('/redirect')
    return render_template('Redirect.html') # Render the html for the redirect page

@app.route('/toHome', methods=['GET', 'POST']) # Page has html that calls fetchUserData, then redirects to home page
def toHome():
    return render_template('toHome.html', fetchUserData=fetchUserData)

@app.route('/homePage', methods=['GET', 'POST']) # Home Page site
def homePage():
    global page_history
    page_history.append('/homePage')
    if 'id' in request.form: # Has the 'Convert' button been pressed?
        # If so, go to convertingPlaylist site and set the spotify_playlist_id varible to the id corresponding to the button pressed
        global spotify_playlist_id
        global playlist_converted
        playlist_converted = False
        spotify_playlist_id = request.form['id']
        return redirect(url_for('convertingPlaylist'))
    elif 'Help' in request.form:
        return redirect('/help')
    elif 'different_playlist' in request.form:
        return redirect('/differentPlaylist')
    return render_template('HomePage.html', playlists=user_playlists) # Render Home Page html

@app.route('/convertingPlaylist', methods=['GET', 'POST']) # Site that displays 'Converting Playlist' message
def convertingPlaylist():
    global page_history
    page_history.append('/convertingPlaylist')
    return render_template('ConvertingPlaylist.html')


@app.route('/toPlaylistConverted', methods=['GET', 'POST']) # Intermidiate page between playlist converting and playlist converted pages (calls main() function)
def toPlaylistConverted():
    return render_template('toPlaylistConverted.html', main=main)


@app.route('/playlistConverted', methods=['GET', 'POST']) # Site for once the playlist has finished converting
def playlistConverted():
    global page_history
    global spotify_playlist
    global spotify_playlist_id
    page_history.append('\playlistConverted')
    if 'error' in spotify_playlist or spotify_playlist_id == '':
        if 'try_again' in request.form: # Has the button to try again been pressed?
            return redirect('/differentPlaylist') # If so, redirect to /differentPlaylist page
        elif 'home_page' in request.form: # Has the button to go back to the home page been pressed?
            return redirect('/homePage') # If so, redirect user to home page    
        elif 'Help' in request.form:
            return redirect('/help')    
        return render_template('PlaylistNotFound.html')

    if 'open_playlist' in request.form: # Has the button to open the playlist been pressed?
        webbrowser.open(youtube_playlist_url) # If so, open the playlist in a new tab on the web browser
    elif 'home_page' in request.form: # Has the button to go back to the home page been pressed?
        return redirect('/homePage') # If so, redirect user to home page
    elif 'Help' in request.form:
        return redirect('/help')
    return render_template('PlaylistConverted.html') # Render html for page

@app.route('/help', methods=['GET', 'POST']) # Help page
def help():
    if 'Back' in request.form: # Has the button to go back been pressed?
        previous_page = page_history[-1] # Store previous page from page_history
        page_history.pop() # Removes previous page
        return redirect(previous_page) # Redircts to previos page
    elif 'HomePage' in request.form: # Has the button to go back to the home page been pressed?
        return redirect('/homePage') # If so, redirect user to home page
    return render_template('Help.html')

@app.route('/differentPlaylist', methods=['GET', 'POST']) # Page to select a different playlist
def differentPlaylist():
    global page_history
    global spotify_playlist_id
    global playlist_converted
    if 'playlist_id' in request.form: # Has the 'convert' been pressed
        playlist_converted = False
        spotify_playlist_id = request.form['playlist_id']
        return redirect(url_for('convertingPlaylist')) # Convert playlist
    elif 'Back' in request.form: # Has the button to go back been pressed?
        previous_page = page_history[-1] # Store previous page from page_history
        page_history.pop() # Removes previous page
        return redirect(previous_page) # Redircts to previos page
    elif 'Help' in request.form: # Has help button been pressed?
        # If so, store current page as previous page and redirect user to help page
        page_history.append('/differentPlaylist')
        return redirect('/help')

    return render_template('DifferentPlaylist.html')

#  Creates spotify Oauth client
def createSpotifyOAuth():
    return SpotifyOAuth(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri=url_for('redirectPage', _external=True),
        scope='user-read-private'
    )

if __name__ == "__main__":
    webbrowser.open('http://127.0.0.1:5000') #  Opens site on webbrowser automatically
    app.run(port=5000, host='0.0.0.0') #  Runs flask application