## Features

- Download stickers from Line.
- Download songs, albums or playlists from Deezer (with a Deezer or Spotify link).
- Play songs in vc, with the **best possible audio quality (Opus 510kbps),** regardless the bitrate of the channel you are in.
- Set default file format/bitrate (Available: FLAC, MP3 320 or MP3 128).

## To do:

- Add info embeds
- Finish the music player:
  - Add the possibility to search a song instead of giving a deezer/spotify link
  - Add a command to make the bot leave/stop
  - ...
- Improve queue design
- Add download modes (eg. upload songs one by one for albums/playlists).
- Auto detect the availability of a song and set an ARL from where the song is available
- Add the ability to /vc play an entire playlist/album at once

## Known bug:

- Can't download most animated stickers on LINE when downloaded using GIF format: "TypeError: color must be int or single-element tuple"

Some of the code for the player comes from [this github gist](https://gist.github.com/aliencaocao/83690711ef4b6cec600f9a0d81f710e5) !
