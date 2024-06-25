## Features

- Download stickers from LINE.
- Download songs, albums or playlists from Deezer (with a Deezer or Spotify link).
- Play songs in vc, with the **best possible audio quality**.
  - Bypasses the channel's audio bitrate.
  - Audio taken from lossless files, then converted to Opus 510kbps.
- Play songs/videos in vc from Youtube, with standard audio quality.
- Set default file format/bitrate (Available: FLAC, MP3 320 or MP3 128).
- Chat (using GPT-4o)

## To do:

- Finish the music player:
  - Add the possibility to add an entire album in queue (/vc play).
  - Add a command to pop songs from queue list.
  - ...
- Add a /meaning command, to search the meaning (+sentence/pitch accent/...) of a Japanese word.
- Improve queue design.
- Add download modes (eg. upload songs one by one for albums/playlists).
- Auto detect the availability of a song and set an ARL from where the song is available.
- Add the ability to /vc play an entire playlist/album at once.

## Known bugs:

- Clips at default volume (because of the lack of volume control with opus format).

Most of the code of the player comes from [this github gist](https://gist.github.com/aliencaocao/83690711ef4b6cec600f9a0d81f710e5) !
