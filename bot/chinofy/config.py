import datetime
from pathlib import Path

id: str = str(datetime.datetime.timestamp(datetime.datetime.now())).replace('.', '')

CONFIG = {
    'SAVE_CREDENTIALS':           True                                                              ,
    'CREDENTIALS_LOCATION':       ''                                                                ,
    'OUTPUT':                     '{artist} - {song_name}.{ext}'                                    ,
    'SONG_ARCHIVE':               ''                                                                ,
    'ROOT_PATH':                  Path('.').absolute() / 'output' / 'vc_songs' / 'OGG 320' / id     ,
    'ROOT_PODCAST_PATH':          Path('.').absolute() / 'output' / 'vc_podcasts' / id              ,
    'SPLIT_ALBUM_DISCS':          False                                                             ,
    'DOWNLOAD_LYRICS':            True                                                              ,
    'MD_SAVE_GENRES':             False                                                             ,
    'MD_ALLGENRES':               False                                                             ,
    'MD_GENREDELIMITER':          ','                                                               ,
    'DOWNLOAD_FORMAT':            'ogg'                                                             ,
    'DOWNLOAD_QUALITY':           'auto'                                                            ,
    'TRANSCODE_BITRATE':          'auto'                                                            ,
    'RETRY_ATTEMPTS':             1                                                                 ,
    'BULK_WAIT_TIME':             1                                                                 ,
    'OVERRIDE_AUTO_WAIT':         False                                                             ,
    'CHUNK_SIZE':                 20000                                                             ,
    'DOWNLOAD_REAL_TIME':         False                                                             ,
    'LANGUAGE':                   'en'                                                              ,
    'PRINT_SPLASH':               False                                                             ,
    'PRINT_SKIPS':                True                                                              ,
    'PRINT_DOWNLOAD_PROGRESS':    True                                                              ,
    'PRINT_ERRORS':               True                                                              ,
    'PRINT_DOWNLOADS':            False                                                             ,
    'PRINT_API_ERRORS':           True                                                              ,
    'PRINT_PROGRESS_INFO':        True                                                              ,
    'PRINT_WARNINGS':             True                                                              ,
    'TEMP_DOWNLOAD_DIR':          ''                                                                ,
}