import os
from os.path import join, dirname
from dotenv import load_dotenv
import pychromecast
from google.cloud import storage
from google.cloud import texttospeech
from datetime import timedelta

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

account_json = 'service-account.json'

gcs_cli = storage.Client.from_service_account_json(account_json)
bucket = gcs_cli.get_bucket(os.environ.get('BUCKET_NAME'))

tts_cli = texttospeech.TextToSpeechClient.from_service_account_json(
    account_json)


def find_device(ip_addr):
    device = pychromecast.Chromecast(ip_addr)
    return device


def send_sound(device, audio_url):
    mc = device.media_controller
    mc.play_media(audio_url, 'audio/mp3', autoplay=True)
    mc.block_until_active()


def make_synthesis_args(
    text,
    lang='ja-JP',
    gender=texttospeech.enums.SsmlVoiceGender.NEUTRAL,
    volume=8.0,
    speed=1.2,
    profile='small-bluetooth-speaker-class-device',
):
    synthesis_input = texttospeech.types.SynthesisInput(text=text)
    voice = texttospeech.types.VoiceSelectionParams(
        language_code=lang,
        ssml_gender=gender)
    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3,
        volume_gain_db=volume,
        speaking_rate=speed,
        effects_profile_id=[profile])
    return (synthesis_input, voice, audio_config)


def generate_audio_url(text, audio_config=None):
    filename = 'audio.mp3'
    filepath = f'tts-audio/{filename}'
    filepath_local = f'./tts-audio/{filename}'

    if audio_config is None:
        audio_config = {}

    response = tts_cli.synthesize_speech(
        *make_synthesis_args(text=text, **audio_config))

    # The response's audio_content is binary.
    with open(filepath_local, 'wb') as out:
        # Write the response to the output file.
        out.write(response.audio_content)

    blob = bucket.blob(filepath)
    blob.upload_from_filename(filepath_local)

    return blob.generate_signed_url(expiration=timedelta(minutes=1))


if __name__ == '__main__':
    home = find_device(os.environ.get('IP_ADDR'))
    home.wait()

    audio_url = generate_audio_url(text='できました', audio_config={
        'speed': 1.4,
    })

    send_sound(home, audio_url)
