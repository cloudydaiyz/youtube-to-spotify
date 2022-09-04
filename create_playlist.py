import json
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import requests
import youtube_dl

from secrets import spotify_token, spotify_user_id

class CreatePlaylist:

    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}

    def get_youtube_client(self):
        # From Youtube Data API Website
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes
        )
        credentials = flow.run_console()

        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials = credentials
        )

        return youtube_client

    def get_liked_videos(self):
        # From Youtube Data API
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating="like"
        )
        response = request.execute()

        # Collections information from each video and stores it
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_url = "https://www.youtube.com/watch?v={}".format(item["id"])

            # Use Youtube DL Library to extract information from the video
            video = youtube_dl.YoutubeDL({}).extract_info(
                youtube_url, download=False
            )
            song_info = video["title"].split("-")
            artist = song_info[0]
            song_name = song_info[1]

            # If the song information parsed correctly, add it to our dictionary
            if song_name is not None and artist is not None:
                uri = self.get_spotify_uri(song_name, artist)
                if(uri != ""):
                    self.all_song_info[video_title] = {
                        "youtube_url": youtube_url,
                        "song_name": song_name,
                        "artist": artist,
                        "spotify_uri": uri
                    }

    def create_playlist(self):
        request_body = json.dumps({
            "name": "Youtube Liked Vids",
            "description": "Tasteful music",
            "public": True
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_user_id)
        response = requests.post(
            query,
            data = request_body,
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        # Print out the contents of the response
        response_json = response.json()

        # playlist id
        return response_json["id"]

    def get_spotify_uri(self, song_name, artist):
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )
        response = requests.get(
            query,
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]

        if(len(songs) > 0):
            uri = songs[0]["uri"]
        else:
            print("Unable to download {} by {}".format(song_name, artist))
            return ""
        
        return uri

    def add_song_to_playlist(self):
        self.get_liked_videos()

        # Collect all of the URIs
        uris = [info["spotify_uri"] for song, info in self.all_song_info.items()]

        playlist_id = self.create_playlist()
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        response_json = response.json()
        return response_json


if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()
    