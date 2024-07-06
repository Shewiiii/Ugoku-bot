# Ugoku ! bot
My first discord bot !

## Features

- Download stickers from LINE.
- Download songs, albums or playlists from Deezer (with a Deezer or Spotify link).
- Play songs in vc, with the **best possible audio quality**.
  - Bypasses the channel's audio bitrate.
  - Audio taken from lossless files, then converted to Opus 510kbps if Deezer is the source.
  - Audio taken from OGG 320kbps stream, then converted to Opus 510kbps if Spotify is the source.
- Play songs/videos in vc from Youtube, with standard audio quality.
- Set default file format/bitrate (Available: FLAC, MP3 320 or MP3 128).
- Chat (using GPT-4o)

## To do:

- Finish the music player:
  - Add the possibility to play any uploaded file (for Yuuka-chan ~)
  - Add a loop feature
  - Improve queue design, add markdowns.
  - ...
- Add download modes (eg. upload songs one by one for albums/playlists).

## Known bugs:

- Clips at default volume (because of the lack of volume control with opus format).

Most of the code of the player comes from [this github gist](https://gist.github.com/aliencaocao/83690711ef4b6cec600f9a0d81f710e5) !
